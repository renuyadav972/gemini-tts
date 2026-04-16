"""
Demo — Gemini 3.1 Flash TTS audio tag catalog
==============================================
Generates one short WAV per audio tag so you can hear each rendering in
isolation. The phone call test lets us check "do tags work at all"; this
script produces shareable artifacts that prove each specific tag renders.

Output: data/samples/tag_{name}.wav for each tag.

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
    python scripts/demo_audio_tags.py
"""

import os
import sys
import time
import wave
from pathlib import Path

from google.cloud import texttospeech_v1


MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
VOICE = os.getenv("GEMINI_TTS_VOICE", "Aoede")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "samples"

# Each entry exercises ONE tag in the middle of an otherwise neutral sentence,
# so you can hear the tag's effect clearly vs the surrounding plain speech.
TAGS = [
    ("warm",       "[warm] Hello, thanks for calling. It's really nice to hear from you."),
    ("excited",    "Guess what? [excited] Your package just arrived at the front door!"),
    ("apologetic", "[apologetic] I'm so sorry, that wait was much longer than it should have been."),
    ("whispers",   "Let me tell you something. [whispers] I don't usually share this with everyone."),
    ("laughs",     "That's a good one. [laughs] I did not see that punchline coming."),
    ("sighs",      "[sighs] Alright, let me pull up your account and figure out what happened."),
]


def request_generator(config_request, text: str):
    yield config_request
    yield texttospeech_v1.StreamingSynthesizeRequest(
        input=texttospeech_v1.StreamingSynthesisInput(text=text)
    )


def synth_one(client, voice_params, tag_name: str, text: str) -> dict:
    streaming_config = texttospeech_v1.StreamingSynthesizeConfig(
        voice=voice_params,
        streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.PCM,
            sample_rate_hertz=24000,
        ),
    )
    config_request = texttospeech_v1.StreamingSynthesizeRequest(
        streaming_config=streaming_config
    )

    t0 = time.perf_counter()
    first_chunk_at = None
    chunks = []

    for response in client.streaming_synthesize(request_generator(config_request, text)):
        if first_chunk_at is None:
            first_chunk_at = time.perf_counter()
        chunks.append(response.audio_content)

    total_bytes = sum(len(c) for c in chunks)
    duration_s = total_bytes / (24000 * 2)

    out_path = OUTPUT_DIR / f"tag_{tag_name}.wav"
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"".join(chunks))

    return {
        "tag": tag_name,
        "first_chunk_ms": round((first_chunk_at - t0) * 1000),
        "duration_s": round(duration_s, 2),
        "path": str(out_path),
    }


def main():
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds or not os.path.exists(creds):
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS not set or missing: {creds!r}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = texttospeech_v1.TextToSpeechClient()
    voice = texttospeech_v1.VoiceSelectionParams(
        language_code="en-US", name=VOICE, model_name=MODEL,
    )

    print(f"Model: {MODEL}")
    print(f"Voice: {VOICE}")
    print(f"Output: {OUTPUT_DIR}")
    print()

    results = []
    for tag_name, text in TAGS:
        print(f"  [{tag_name:12}] rendering... ", end="", flush=True)
        try:
            r = synth_one(client, voice, tag_name, text)
            results.append(r)
            print(f"{r['duration_s']}s audio, first chunk in {r['first_chunk_ms']}ms")
        except Exception as e:
            print(f"FAILED: {e}")

    print()
    print(f"Done. {len(results)}/{len(TAGS)} samples written to {OUTPUT_DIR}")
    print()
    print("Play them all:")
    for r in results:
        print(f"  afplay {r['path']}")


if __name__ == "__main__":
    main()
