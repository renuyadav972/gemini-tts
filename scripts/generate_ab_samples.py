"""
Generate A/B samples that show the impact of Gemini TTS features.

Three sets, all single-provider (Gemini 3.1 Flash TTS):

1. Voice character A/B
   Same line through three voices with distinct tonal descriptors so a
   listener can hear what "Breezy" vs "Informative" vs "Upbeat" actually
   means in audio.

2. Director's Notes A/B
   Same transcript rendered two ways: as a bare string, and inside a
   structured prompt (Audio Profile / Scene / Director's Notes / TRANSCRIPT
   delimiter). The transcript text is identical; only the surrounding
   instructions change.

(Plain-vs-tag A/B reuses existing files: data/comparison/gemini_*.wav are
the plain-text versions of the sentences that data/samples/tag_*.wav
render with inline tags. No new generation needed.)

Output: data/samples/ab/{voice,dn}_*.wav

Usage:
    set -a && source .env && set +a
    python scripts/generate_ab_samples.py
"""

import os
import sys
import time
import wave
from pathlib import Path

from google.cloud import texttospeech_v1


MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "samples" / "ab"


VOICE_AB_LINE = "How can I help you today?"
VOICE_AB = [
    ("Aoede", "Breezy"),
    ("Charon", "Informative"),
    ("Puck", "Upbeat"),
]


# Director's Notes gradient: same voice, same transcript, increasing direction.
# Voice is Charon (Informative) — a flatter base than Aoede so direction has
# more visible room to work. Line is deliberately neutral so the prompt
# structure does the lifting.
DN_VOICE = "Charon"
DN_TRANSCRIPT = "Your delivery window is between 4 and 6 PM today."

DIRECTORS_NOTES_GRADIENT = [
    {
        "id": "bare",
        "label": "Bare",
        "prompt": DN_TRANSCRIPT,
    },
    {
        "id": "minor",
        "label": "Minor direction",
        "prompt": (
            "Audio Profile: Friendly, calm.\n"
            "Director's Notes: A touch warmer than neutral, slight emphasis on \"today\".\n\n"
            "#### TRANSCRIPT\n"
            + DN_TRANSCRIPT
        ),
    },
    {
        "id": "major",
        "label": "Major direction",
        "prompt": (
            "Audio Profile: Calm, confident dispatcher in his mid-30s, American English. "
            "Reassuring, never rushed.\n"
            "Scene: He is calling an older customer who specifically asked him to confirm "
            "the delivery time clearly. The customer is hard of hearing.\n"
            "Director's Notes: Slow and deliberate. Brief pause after \"window\". Emphasize "
            "the numbers clearly: \"four ... and six P.M.\" Reassuring, kind, unhurried.\n\n"
            "#### TRANSCRIPT\n"
            + DN_TRANSCRIPT
        ),
    },
    {
        "id": "extreme",
        "label": "Extreme direction",
        "prompt": (
            "Audio Profile: Late-night noir narrator. Slow, weighty, contemplative. "
            "Each phrase carries gravity.\n"
            "Scene: A dim, empty room. Rain on the window. He is reading what should be "
            "a routine delivery confirmation, but every word lands like a verdict.\n"
            "Director's Notes: Cinematic. Long pauses between phrases. Heavy emphasis. "
            "Almost whispered intensity at moments. Each number drops with weight: "
            "\"four ... and six ... P.M.\" The word \"today\" feels final.\n\n"
            "#### TRANSCRIPT\n"
            + DN_TRANSCRIPT
        ),
    },
]


def request_generator(config_request, text):
    yield config_request
    yield texttospeech_v1.StreamingSynthesizeRequest(
        input=texttospeech_v1.StreamingSynthesisInput(text=text)
    )


def synth(client, voice_name: str, text: str, out_path: Path) -> float:
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

    chunks = []
    for resp in client.streaming_synthesize(request_generator(config_req, text)):
        chunks.append(resp.audio_content)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"".join(chunks))

    return sum(len(c) for c in chunks) / (24000 * 2)


def main():
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds or not os.path.exists(creds):
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS not set or missing: {creds!r}")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = texttospeech_v1.TextToSpeechClient()

    print(f"Model: {MODEL}")
    print(f"Output: {OUTPUT_DIR}\n")

    print("Voice character A/B (same line, different voices):")
    for voice_name, descriptor in VOICE_AB:
        out = OUTPUT_DIR / f"voice_{voice_name}.wav"
        try:
            dur = synth(client, voice_name, VOICE_AB_LINE, out)
            print(f"  [{voice_name:8} / {descriptor:12}] {dur:.2f}s → {out.name}")
        except Exception as e:
            print(f"  [{voice_name:8}] FAILED: {e}")

    print(f"\nDirector's Notes gradient ({DN_VOICE}, same line, increasing direction):")
    print(f"  Line: \"{DN_TRANSCRIPT}\"\n")
    for step in DIRECTORS_NOTES_GRADIENT:
        out = OUTPUT_DIR / f"dn_{step['id']}.wav"
        try:
            dur = synth(client, DN_VOICE, step["prompt"], out)
            print(f"  [{step['label']:18}] {dur:.2f}s → {out.name}")
        except Exception as e:
            print(f"  [{step['label']:18}] FAILED: {e}")

    print(f"\nDone. Samples in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
