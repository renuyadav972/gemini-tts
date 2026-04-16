"""
Demo — Gemini 3.1 Flash TTS native multi-speaker
=================================================
Generates a two-voice dialogue in a SINGLE streaming call. This is the
feature Flash Live literally cannot do — it's one voice per session.

For the comparison, this script makes Flash TTS's "cheat code" feature
concrete: one API call, two distinct speakers, coherent pacing, no
stitching between separate generations.

Output: data/samples/multi_speaker_demo.wav

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
    python scripts/demo_multi_speaker.py
"""

import os
import sys
import time
import wave
from pathlib import Path

from google.cloud import texttospeech_v1


MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "samples" / f"multi_speaker_{os.getenv('SPEAKER_1_VOICE', 'Fenrir')}_{os.getenv('SPEAKER_2_VOICE', 'Leda')}.wav"

# Speaker names can be anything — they're labels that the model maps to the
# voices defined in the config. Format the input as "Name: line" lines.
SPEAKER_1 = "Alex"
SPEAKER_1_VOICE = os.getenv("SPEAKER_1_VOICE", "Fenrir")   # typically deeper/male-leaning

SPEAKER_2 = "Riley"
SPEAKER_2_VOICE = os.getenv("SPEAKER_2_VOICE", "Leda")     # typically higher/female-leaning

DIALOGUE = f"""{SPEAKER_1}: Have you tried the new Gemini Flash TTS model?
{SPEAKER_2}: [excited] Yeah, I've been playing with it all morning.
{SPEAKER_1}: What's it actually good for?
{SPEAKER_2}: Honestly? Anywhere you'd script narration. Podcasts, onboarding, voiceovers.
{SPEAKER_1}: [skeptical] But it can't do real-time conversation, right?
{SPEAKER_2}: That's what Flash Live is for. Different tool, different job.
{SPEAKER_1}: Got it. So this is the production voice, not the phone voice.
{SPEAKER_2}: Exactly."""


def request_generator(config_request, text: str):
    yield config_request
    yield texttospeech_v1.StreamingSynthesizeRequest(
        input=texttospeech_v1.StreamingSynthesisInput(text=text)
    )


def main():
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds or not os.path.exists(creds):
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS not set or missing: {creds!r}")
        sys.exit(1)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = texttospeech_v1.TextToSpeechClient()

    # Multi-speaker config: map each speaker label to a prebuilt voice
    multi_speaker_config = texttospeech_v1.MultiSpeakerVoiceConfig(
        speaker_voice_configs=[
            texttospeech_v1.MultispeakerPrebuiltVoice(
                speaker_alias=SPEAKER_1,
                speaker_id=SPEAKER_1_VOICE,
            ),
            texttospeech_v1.MultispeakerPrebuiltVoice(
                speaker_alias=SPEAKER_2,
                speaker_id=SPEAKER_2_VOICE,
            ),
        ]
    )

    voice = texttospeech_v1.VoiceSelectionParams(
        language_code="en-US",
        model_name=MODEL,
        multi_speaker_voice_config=multi_speaker_config,
    )

    streaming_config = texttospeech_v1.StreamingSynthesizeConfig(
        voice=voice,
        streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.PCM,
            sample_rate_hertz=24000,
        ),
    )
    config_request = texttospeech_v1.StreamingSynthesizeRequest(
        streaming_config=streaming_config
    )

    print(f"Model:      {MODEL}")
    print(f"Speaker 1:  {SPEAKER_1} = {SPEAKER_1_VOICE}")
    print(f"Speaker 2:  {SPEAKER_2} = {SPEAKER_2_VOICE}")
    print(f"Dialogue:   {len(DIALOGUE.splitlines())} lines")
    print()
    print("Rendering...")

    t0 = time.perf_counter()
    first_chunk_at = None
    chunks = []

    try:
        responses = client.streaming_synthesize(request_generator(config_request, DIALOGUE))
        for response in responses:
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter()
                print(f"  first chunk at {(first_chunk_at - t0) * 1000:.0f} ms")
            chunks.append(response.audio_content)
    except Exception as e:
        print(f"ERROR: multi-speaker synthesis failed: {e}")
        print()
        print("Likely causes:")
        print("  - Model doesn't support multi-speaker in your region")
        print("  - Voice names don't match the multi-speaker-enabled set")
        sys.exit(2)

    total_bytes = sum(len(c) for c in chunks)
    duration_s = total_bytes / (24000 * 2)

    with wave.open(str(OUTPUT_PATH), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"".join(chunks))

    print()
    print(f"Done. {duration_s:.2f}s dialogue in {(time.perf_counter() - t0) * 1000:.0f}ms total.")
    print(f"Output: {OUTPUT_PATH}")
    print()
    print(f"Play: afplay {OUTPUT_PATH}")
    print()
    print("Listen for: the two voices should sound distinctly different, with")
    print("coherent pacing between turns. No awkward silence or clipped audio")
    print("at speaker transitions. This is the feature Flash Live can't match.")


if __name__ == "__main__":
    main()
