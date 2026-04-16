"""
Demo — Sample 8 Gemini Flash TTS voices with the same line
===========================================================
Same sentence, same language, 8 different voices. Use this to figure
out which voices are actually distinct from each other so you can pick
the right pair for the multi-speaker test.

Output: data/samples/voice_{name}.wav
"""

import os
import sys
import time
import wave
from pathlib import Path

from google.cloud import texttospeech_v1

MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "samples"

# Pick 8 voices that Google's naming suggests should cover different timbres.
# Google doesn't publicly document gender/pitch per voice; these are picked
# based on the name conventions in early reviews. We'll hear which is which.
VOICES = [
    "Aoede",        # our default
    "Puck",
    "Kore",
    "Fenrir",       # often described as deeper/male
    "Leda",         # often described as higher/female
    "Charon",       # often described as lower pitch
    "Zephyr",
    "Orus",
]

SAMPLE_TEXT = (
    "Hi, I'm testing my voice. This is a one-sentence sample so you can "
    "hear what I sound like."
)


def request_generator(config_request, text):
    yield config_request
    yield texttospeech_v1.StreamingSynthesizeRequest(
        input=texttospeech_v1.StreamingSynthesisInput(text=text)
    )


def main():
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds or not os.path.exists(creds):
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS not set")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = texttospeech_v1.TextToSpeechClient()

    print(f"Model: {MODEL}")
    print(f"Rendering {len(VOICES)} voices, same sentence...\n")

    for voice_name in VOICES:
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code="en-US", name=voice_name, model_name=MODEL,
        )
        cfg = texttospeech_v1.StreamingSynthesizeConfig(
            voice=voice,
            streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
                audio_encoding=texttospeech_v1.AudioEncoding.PCM,
                sample_rate_hertz=24000,
            ),
        )
        config_req = texttospeech_v1.StreamingSynthesizeRequest(streaming_config=cfg)

        t0 = time.perf_counter()
        chunks = []
        try:
            for resp in client.streaming_synthesize(request_generator(config_req, SAMPLE_TEXT)):
                chunks.append(resp.audio_content)
        except Exception as e:
            print(f"  [{voice_name:10}] FAILED: {e}")
            continue

        out = OUTPUT_DIR / f"voice_{voice_name}.wav"
        with wave.open(str(out), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(b"".join(chunks))

        dur = sum(len(c) for c in chunks) / (24000 * 2)
        print(f"  [{voice_name:10}] {dur:.1f}s → {out.name}")

    print(f"\nPlay them all back to back:")
    for v in VOICES:
        print(f"  afplay {OUTPUT_DIR / f'voice_{v}.wav'}")


if __name__ == "__main__":
    main()
