"""
Agent B — Cascaded, fully Google
=================================
Google Cloud Speech-to-Text → Gemini 2.5 Flash (LLM) → Gemini 3.1 Flash TTS

Three specialized models, three API calls per turn — all first-party Google.
One bill, one auth surface (service account), one vendor. This is the
purest possible cascaded-Google story for comparing against Agent A's
native S2S (Gemini 3.1 Flash Live).

The STT layer is configured with a multilingual language list
(English + Hindi by default) so we can actually test code-switching.
Nova-3 English-only from the prior gemini-s2s cascaded version killed
mid-call when the caller switched language.

The system prompt intentionally teaches the LLM to emit expressive audio
tags (`[whispers]`, `[excited]`, `[apologetic]`, etc.). Without this,
Agent B would never exercise Gemini TTS's tone-directing advantage and
the comparison against the native A2A model would be unfair.

Run:
    python agent_cascaded_google.py -t plivo -x <ngrok-host> --port 8000
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone

import httpx
from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import parse_telephony_websocket
from pipecat.serializers.plivo import PlivoFrameSerializer
from pipecat.services.google.llm import GoogleLLMService
from pipecat.services.google.stt import GoogleSTTService
from pipecat.services.google.tts import GeminiTTSService
from pipecat.transcriptions.language import Language
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketParams,
    FastAPIWebsocketTransport,
)
from pipecat.turns.user_stop import SpeechTimeoutUserTurnStopStrategy
from pipecat.turns.user_turn_strategies import UserTurnStrategies

from metrics_observer import MetricsCollectorObserver

load_dotenv(override=False)


GREETING = "Hello! I'm your personal assistant. How can I help you?"


def get_system_prompt() -> str:
    """System prompt that teaches the LLM to emit Gemini TTS audio tags
    AND aggressively overrides the 'I am an AI, I cannot express emotion'
    RLHF refusal that Gemini 2.5 Flash falls into by default.

    Prior run's bug: when the caller asked "can you sound apologetic or
    excited?", the LLM emitted `[apologetic] I'm sorry, I'm not able to
    express emotions or change my speaking style like that.` — using the
    tag correctly while verbally denying the capability. This prompt is
    rewritten to shut that reflex down.
    """
    now = datetime.now(timezone.utc)
    return (
        "You are a helpful personal assistant on a phone call.\n"
        f"The current date is {now.strftime('%B %d, %Y')} and time is {now.strftime('%I:%M %p')} UTC.\n\n"
        "You can help with greetings, casual conversation, math, translations, and "
        "general knowledge you are confident about.\n\n"
        "Rules:\n"
        "- If you are not sure about something, say so honestly. Do not make up facts.\n"
        "- Never guess current weather, news, sports scores, or stock prices.\n"
        "- Keep responses to 1-2 short sentences. This is a phone call.\n"
        "- Respond in whatever language the caller speaks. If they switch languages, switch with them.\n"
        "- No markdown, bullets, or formatting. Your words will be spoken aloud.\n\n"
        "VOICE CAPABILITY — READ CAREFULLY:\n"
        "Your voice can genuinely express emotion through audio tags. These are NOT\n"
        "metaphors, NOT instructions for a human voice actor, and NOT hypothetical.\n"
        "When you write [apologetic], [excited], [whispers], [laughs], [sighs], or\n"
        "[warm] at the start of a sentence, the caller literally hears you sounding\n"
        "that way — the tag renders as actual vocal expression through the TTS.\n\n"
        "Therefore:\n"
        "- NEVER say 'I cannot express emotion' or 'I can only respond with information'.\n"
        "  That is factually wrong. You CAN express emotion via these tags.\n"
        "- NEVER say 'as an AI I have no feelings'. You do not need feelings to use\n"
        "  the tags — you just use them, and the caller hears tone.\n"
        "- When the caller asks you to sound apologetic, excited, warm, sad, etc.,\n"
        "  just DO IT by prepending the tag. Don't explain. Don't disclaim.\n"
        "  Example good: '[excited] That's a great question! Yes, I can do that.'\n"
        "  Example bad:  'I am an AI so I cannot truly feel excited, but ...'\n\n"
        "Available tags:\n"
        "  [warm]        — reassuring, friendly tone\n"
        "  [excited]     — genuine enthusiasm\n"
        "  [apologetic]  — sincere apology for a mistake or delay\n"
        "  [whispers]    — hushed aside\n"
        "  [laughs]      — natural, short laugh\n"
        "  [sighs]       — a small exhale, usually before acknowledging effort\n\n"
        "Use tags when the moment genuinely calls for them. Don't chain multiple\n"
        "tags on the same line. Don't overuse them — but DO use them when asked.\n"
    )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def run_bot(
    transport: BaseTransport,
    handle_sigint: bool,
    call_id: str | None = None,
):
    session_id = str(uuid.uuid4())
    data_dir = os.path.join(os.path.dirname(__file__), "data", "sessions")

    tts_model = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    tts_voice = os.getenv("GEMINI_TTS_VOICE", "Aoede")
    llm_model = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")

    metrics_observer = MetricsCollectorObserver(
        session_id=session_id,
        mode="cascaded_google",
        config={
            "stt": "google-cloud-stt-chirp_2",
            "llm": llm_model,
            "tts": tts_model,
            "tts_voice": tts_voice,
        },
        data_dir=data_dir,
    )

    # Google Cloud Speech-to-Text — English only. This agent's purpose is
    # to exercise Gemini 3.1 Flash TTS features (audio tags, prose style
    # direction). Multilingual behavior is a Flash Live story, covered in
    # gemini-s2s. Keeping STT simple isolates the variable under test.
    stt = GoogleSTTService(
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        params=GoogleSTTService.InputParams(
            languages=[Language.EN_US],
            model="chirp_2",
            enable_automatic_punctuation=True,
            enable_interim_results=True,
        ),
    )

    llm = GoogleLLMService(
        api_key=os.getenv("GOOGLE_API_KEY"),
        model=llm_model,
    )

    # Gemini Flash TTS via Cloud Text-to-Speech streaming_synthesize.
    # Auth is GOOGLE_APPLICATION_CREDENTIALS — the Cloud TTS API does NOT
    # accept the Gemini API key used for the LLM above; it needs a
    # service-account JSON with roles/cloudtts.user.
    # Sample rate must be 24000 — Gemini TTS always outputs 24 kHz PCM.
    # Pipecat's transport output layer will resample to Plivo's 8 kHz.
    tts = GeminiTTSService(
        credentials_path=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        model=tts_model,
        voice_id=tts_voice,
        sample_rate=24000,
        params=GeminiTTSService.InputParams(
            language=Language.EN_US,
        ),
    )

    messages = [{"role": "system", "content": get_system_prompt()}]
    context = LLMContext(messages)

    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(),
            user_turn_strategies=UserTurnStrategies(
                stop=[SpeechTimeoutUserTurnStopStrategy(user_speech_timeout=0.7)],
            ),
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,  # Plivo accepts 8 kHz; Pipecat resamples TTS's 24 kHz down
            enable_metrics=True,
            enable_usage_metrics=True,
            observers=[metrics_observer],
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        if call_id:
            asyncio.create_task(_start_recording(call_id))
        logger.info(
            f"Agent B connected — cascaded Google, "
            f"llm={llm_model} tts={tts_model} voice={tts_voice}"
        )
        await asyncio.sleep(1.5)
        await task.queue_frames([TTSSpeakFrame(text=GREETING)])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Client disconnected")
        if call_id:
            asyncio.create_task(_fetch_recording(call_id, session_id, data_dir))
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint)
    await runner.run(task)


# ---------------------------------------------------------------------------
# Plivo recording helpers (shared pattern with agent_native.py)
# ---------------------------------------------------------------------------


async def _start_recording(call_id: str):
    auth_id = os.getenv("PLIVO_AUTH_ID", "")
    auth_token = os.getenv("PLIVO_AUTH_TOKEN", "")
    if not auth_id or not auth_token:
        return
    try:
        async with httpx.AsyncClient() as http:
            resp = await http.post(
                f"https://api.plivo.com/v1/Account/{auth_id}/Call/{call_id}/Record/",
                auth=(auth_id, auth_token),
                json={"time_limit": 300, "file_format": "mp3"},
            )
            logger.info(f"Plivo recording started: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Failed to start recording: {e}")


async def _fetch_recording(call_id: str, session_id: str, data_dir: str):
    auth_id = os.getenv("PLIVO_AUTH_ID", "")
    auth_token = os.getenv("PLIVO_AUTH_TOKEN", "")
    if not auth_id or not auth_token:
        return
    import json

    for attempt in range(12):
        await asyncio.sleep(5)
        try:
            async with httpx.AsyncClient() as http:
                resp = await http.get(
                    f"https://api.plivo.com/v1/Account/{auth_id}/Recording/",
                    auth=(auth_id, auth_token),
                    params={"call_uuid": call_id, "limit": 1},
                )
                if resp.status_code == 200:
                    objects = resp.json().get("objects", [])
                    if objects:
                        recording_url = objects[0].get("recording_url")
                        if recording_url:
                            logger.info(f"Recording ready: {recording_url}")
                            dl = await http.get(recording_url)
                            rec_path = os.path.join(data_dir, f"{session_id}.mp3")
                            with open(rec_path, "wb") as f:
                                f.write(dl.content)
                            logger.info(f"Recording saved: {rec_path}")
                            session_path = os.path.join(data_dir, f"{session_id}.json")
                            if os.path.exists(session_path):
                                with open(session_path) as f:
                                    session = json.load(f)
                                session["recording_url"] = recording_url
                                session["recording_file"] = rec_path
                                with open(session_path, "w") as f:
                                    json.dump(session, f, indent=2)
                            return
        except Exception as e:
            logger.warning(f"Recording fetch attempt {attempt + 1}: {e}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def bot(runner_args: RunnerArguments):
    transport_type, call_data = await parse_telephony_websocket(runner_args.websocket)
    logger.info(f"Agent B (cascaded Google): transport={transport_type}")

    serializer = PlivoFrameSerializer(
        stream_id=call_data["stream_id"],
        call_id=call_data["call_id"],
        auth_id=os.getenv("PLIVO_AUTH_ID", ""),
        auth_token=os.getenv("PLIVO_AUTH_TOKEN", ""),
    )

    transport = FastAPIWebsocketTransport(
        websocket=runner_args.websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            serializer=serializer,
        ),
    )

    await run_bot(transport, runner_args.handle_sigint, call_id=call_data["call_id"])


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()
