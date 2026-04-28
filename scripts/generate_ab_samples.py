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


DIRECTORS_NOTES_PAIRS = [
    {
        "id": "empathetic",
        "transcript": "I'm sorry to hear about that. Let me see what I can do.",
        "directed_prompt": (
            "Audio Profile: Young female, late 20s, friendly American English, slight warmth.\n"
            "Scene: Maya is responding to a customer who is frustrated about a delayed package, "
            "on a busy weekday afternoon.\n"
            "Director's Notes: Genuinely empathetic, calm, confident. A small pause after "
            "\"I'm sorry to hear about that\" to give the line emotional weight. Steady pace.\n\n"
            "#### TRANSCRIPT\n"
            "I'm sorry to hear about that. Let me see what I can do."
        ),
    },
    {
        "id": "upbeat",
        "transcript": "Great news, your order is ready for pickup.",
        "directed_prompt": (
            "Audio Profile: Energetic young female, late 20s, friendly American English.\n"
            "Scene: Calling a customer to share good news about their order being ready early.\n"
            "Director's Notes: Genuine excitement, warm not bubbly. Clear emphasis on "
            "\"Great news\" and \"ready\". Slightly faster than neutral pace, lifting on \"ready\".\n\n"
            "#### TRANSCRIPT\n"
            "Great news, your order is ready for pickup."
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

    print("\nDirector's Notes A/B (same transcript, bare vs directed):")
    voice_for_dn = "Aoede"
    for pair in DIRECTORS_NOTES_PAIRS:
        for kind, text in [("bare", pair["transcript"]), ("directed", pair["directed_prompt"])]:
            out = OUTPUT_DIR / f"dn_{pair['id']}_{kind}.wav"
            try:
                dur = synth(client, voice_for_dn, text, out)
                print(f"  [{pair['id']:12} / {kind:8}] {dur:.2f}s → {out.name}")
            except Exception as e:
                print(f"  [{pair['id']:12} / {kind:8}] FAILED: {e}")

    print(f"\nDone. Samples in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
