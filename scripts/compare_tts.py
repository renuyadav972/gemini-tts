"""
Compare TTS quality: Gemini Flash TTS vs ElevenLabs Flash v2.5 vs Cartesia Sonic.

Same 6 sentences through all three providers. Outputs WAV files for side-by-side listening.

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
    export ELEVENLABS_API_KEY=sk_...
    export CARTESIA_API_KEY=sk_car_...
    python scripts/compare_tts.py
"""

import os
import sys
import time
import wave
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "comparison"

# Same sentences, NO audio tags (tags are Gemini-specific; fair comparison
# uses plain text so we're comparing raw voice quality, not feature support)
SENTENCES = [
    ("greeting",    "Hello, thanks for calling. It's really nice to hear from you."),
    ("excited",     "Guess what? Your package just arrived at the front door!"),
    ("apologetic",  "I'm so sorry, that wait was much longer than it should have been."),
    ("quiet",       "Let me tell you something. I don't usually share this with everyone."),
    ("amused",      "That's a good one. I did not see that punchline coming."),
    ("resigned",    "Alright, let me pull up your account and figure out what happened."),
]


def generate_gemini(sentences):
    """Generate via Cloud TTS streaming (same path as our tests)."""
    from google.cloud import texttospeech_v1

    MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
    VOICE = "Aoede"

    client = texttospeech_v1.TextToSpeechClient()
    voice = texttospeech_v1.VoiceSelectionParams(
        language_code="en-US", name=VOICE, model_name=MODEL,
    )
    cfg = texttospeech_v1.StreamingSynthesizeConfig(
        voice=voice,
        streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.PCM,
            sample_rate_hertz=24000,
        ),
    )

    def req_gen(text):
        yield texttospeech_v1.StreamingSynthesizeRequest(streaming_config=cfg)
        yield texttospeech_v1.StreamingSynthesizeRequest(
            input=texttospeech_v1.StreamingSynthesisInput(text=text)
        )

    results = []
    for name, text in sentences:
        t0 = time.perf_counter()
        chunks = []
        first_at = None
        for resp in client.streaming_synthesize(req_gen(text)):
            if first_at is None:
                first_at = time.perf_counter()
            chunks.append(resp.audio_content)
        elapsed = time.perf_counter() - t0
        pcm = b"".join(chunks)

        path = OUTPUT_DIR / f"gemini_{name}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)

        dur = len(pcm) / (24000 * 2)
        ttfb = (first_at - t0) * 1000 if first_at else 0
        results.append({"name": name, "ttfb_ms": round(ttfb), "duration_s": round(dur, 2), "path": str(path)})
        print(f"    [{name:12}] {dur:.1f}s, ttfb {ttfb:.0f}ms")

    return results


def generate_elevenlabs(sentences):
    """Generate via ElevenLabs streaming API."""
    from elevenlabs import ElevenLabs

    client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    # Alexandra — ElevenLabs' recommended conversational agent voice
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "kdmDKE6EkgrWrrykO9Qt")

    results = []
    for name, text in sentences:
        t0 = time.perf_counter()
        first_at = None
        chunks = []

        audio_gen = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id="eleven_flash_v2_5",
            output_format="pcm_24000",
        )
        for chunk in audio_gen:
            if first_at is None:
                first_at = time.perf_counter()
            chunks.append(chunk)

        elapsed = time.perf_counter() - t0
        pcm = b"".join(chunks)

        path = OUTPUT_DIR / f"elevenlabs_{name}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)

        dur = len(pcm) / (24000 * 2)
        ttfb = (first_at - t0) * 1000 if first_at else 0
        results.append({"name": name, "ttfb_ms": round(ttfb), "duration_s": round(dur, 2), "path": str(path)})
        print(f"    [{name:12}] {dur:.1f}s, ttfb {ttfb:.0f}ms")

    return results


def generate_cartesia(sentences):
    """Generate via Cartesia streaming API."""
    from cartesia import Cartesia

    client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))
    # Katie — Cartesia's recommended stable voice for agents
    voice_id = os.getenv("CARTESIA_VOICE_ID", "f786b574-daa5-4673-aa0c-cbe3e8534c02")

    results = []
    for name, text in sentences:
        t0 = time.perf_counter()
        first_at = None
        chunks = []

        output = client.tts.bytes(
            model_id="sonic-3",
            transcript=text,
            voice={"mode": "id", "id": voice_id},
            output_format={
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 24000,
            },
        )

        chunks_bytes = []
        for b in output:
            if first_at is None:
                first_at = time.perf_counter()
            chunks_bytes.append(b)
        pcm = b"".join(chunks_bytes)

        elapsed = time.perf_counter() - t0

        path = OUTPUT_DIR / f"cartesia_{name}.wav"
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(24000)
            w.writeframes(pcm)

        dur = len(pcm) / (24000 * 2)
        ttfb = (first_at - t0) * 1000 if first_at else 0
        results.append({"name": name, "ttfb_ms": round(ttfb), "duration_s": round(dur, 2), "path": str(path)})
        print(f"    [{name:12}] {dur:.1f}s, ttfb {ttfb:.0f}ms")

    return results


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output: {OUTPUT_DIR}\n")

    print("Gemini 3.1 Flash TTS (Aoede):")
    print("(Matched character: warm/conversational female across all three)\n")
    try:
        gemini = generate_gemini(SENTENCES)
    except Exception as e:
        print(f"  FAILED: {e}")
        gemini = []

    print("\nElevenLabs Flash v2.5 (Alexandra):")
    try:
        elevenlabs = generate_elevenlabs(SENTENCES)
    except Exception as e:
        print(f"  FAILED: {e}")
        elevenlabs = []

    print("\nCartesia Sonic 3 (Katie):")
    try:
        cartesia = generate_cartesia(SENTENCES)
    except Exception as e:
        print(f"  FAILED: {e}")
        cartesia = []

    # Summary
    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"\n{'Sentence':<14} {'Gemini TTFB':>12} {'EL TTFB':>12} {'Cartesia TTFB':>14}")
    print("-" * 54)
    for i, (name, _) in enumerate(SENTENCES):
        g = gemini[i]["ttfb_ms"] if i < len(gemini) else "n/a"
        e = elevenlabs[i]["ttfb_ms"] if i < len(elevenlabs) else "n/a"
        c = cartesia[i]["ttfb_ms"] if i < len(cartesia) else "n/a"
        print(f"{name:<14} {str(g) + ' ms':>12} {str(e) + ' ms':>12} {str(c) + ' ms':>14}")

    print(f"\nPlay side by side:")
    for name, _ in SENTENCES:
        print(f"  {name}:")
        print(f"    afplay {OUTPUT_DIR}/gemini_{name}.wav")
        print(f"    afplay {OUTPUT_DIR}/elevenlabs_{name}.wav")
        print(f"    afplay {OUTPUT_DIR}/cartesia_{name}.wav")


if __name__ == "__main__":
    main()
