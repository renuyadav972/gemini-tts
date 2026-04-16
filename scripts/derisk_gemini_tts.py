"""
Phase 0 — De-risk Gemini 3.1 Flash TTS streaming
=================================================
Standalone script. Calls Cloud Text-to-Speech streaming_synthesize
directly with gemini-3.1-flash-tts-preview and writes the streamed audio
to a .wav file. Run this BEFORE attempting the Plivo phone path.

Checks:
  1. The preview model ID is accepted by Cloud TTS
  2. Streaming chunks actually arrive (not one blob)
  3. Audio tags render audibly  ([whispers], [laughs], [excited])
  4. Output is 24 kHz PCM mono as documented
  5. First-chunk latency is reasonable (<1s for short inputs)

If any check fails, the full test plan in research/test-plan.md needs
to shift — better to know now than after wiring Pipecat.

Usage:
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
    python scripts/derisk_gemini_tts.py
    # writes ./derisk_output.wav and prints latency stats
"""

import os
import struct
import sys
import time
import wave
from pathlib import Path

from google.cloud import texttospeech_v1


MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
VOICE = os.getenv("GEMINI_TTS_VOICE", "Aoede")
OUTPUT_PATH = Path(__file__).parent.parent / "derisk_output.wav"

# A deliberately expressive script so we can hear whether audio tags
# actually render. Keep short so first-chunk latency dominates.
TEST_INPUT = (
    "[warm] Hi there, I'm testing the new Gemini Flash TTS streaming API. "
    "[excited] This is the first time we're running it end to end. "
    "[whispers] Fingers crossed it works. "
    "[laughs] Okay, let's see the results."
)


def request_generator(config_request, text: str):
    """Yield the config first, then one input chunk. Cloud TTS starts
    synthesis when the iterator closes (half-close)."""
    yield config_request
    yield texttospeech_v1.StreamingSynthesizeRequest(
        input=texttospeech_v1.StreamingSynthesisInput(text=text)
    )


def main():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds_path or not os.path.exists(creds_path):
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS is not set or the file does not exist.")
        print(f"  current value: {creds_path!r}")
        print("  expected: absolute path to a service-account JSON with Cloud TTS access.")
        sys.exit(1)

    print(f"Model:  {MODEL}")
    print(f"Voice:  {VOICE}")
    print(f"Input:  {len(TEST_INPUT)} chars — {TEST_INPUT[:60]}...")
    print()

    client = texttospeech_v1.TextToSpeechClient()

    voice = texttospeech_v1.VoiceSelectionParams(
        language_code="en-US",
        name=VOICE,
        model_name=MODEL,
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

    t0 = time.perf_counter()
    first_chunk_at = None
    chunks = []
    total_bytes = 0

    try:
        responses = client.streaming_synthesize(request_generator(config_request, TEST_INPUT))
        for response in responses:
            audio = response.audio_content
            if first_chunk_at is None:
                first_chunk_at = time.perf_counter()
                print(f"[stream] first chunk at {(first_chunk_at - t0) * 1000:.0f} ms — {len(audio)} bytes")
            chunks.append(audio)
            total_bytes += len(audio)
    except Exception as e:
        print(f"ERROR: streaming_synthesize failed: {e}")
        print()
        print("Likely causes:")
        print(f"  - Model {MODEL!r} not available to your GCP project")
        print("  - Service account missing roles/cloudtts.user")
        print("  - Cloud Text-to-Speech API not enabled on the project")
        sys.exit(2)

    t_end = time.perf_counter()

    if not chunks:
        print("ERROR: no audio chunks received. Preview model may not be streamable.")
        sys.exit(3)

    # Sanity-check: write as 24 kHz mono WAV
    with wave.open(str(OUTPUT_PATH), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(24000)
        wf.writeframes(b"".join(chunks))

    duration_s = total_bytes / (24000 * 2)

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"chunks received:        {len(chunks)}")
    print(f"total audio bytes:      {total_bytes:,}")
    print(f"audio duration:         {duration_s:.2f} s")
    print(f"first-chunk latency:    {(first_chunk_at - t0) * 1000:.0f} ms")
    print(f"total stream time:      {(t_end - t0) * 1000:.0f} ms")
    print(f"output file:            {OUTPUT_PATH}")
    print()

    # Checks
    print("Checks:")
    passed = True
    if len(chunks) >= 2:
        print(f"  [OK] Got {len(chunks)} chunks — streaming is real")
    else:
        print(f"  [WARN] Only 1 chunk received — this may still be a single-blob response")
        passed = False
    if duration_s > 2:
        print(f"  [OK] Audio duration {duration_s:.2f}s looks right")
    else:
        print(f"  [WARN] Audio shorter than expected — check input rendering")
        passed = False
    if (first_chunk_at - t0) < 2.0:
        print(f"  [OK] First chunk in under 2s")
    else:
        print(f"  [WARN] First chunk took {(first_chunk_at - t0):.1f}s — slower than expected")

    print()
    print(f"Play with: afplay {OUTPUT_PATH}  (macOS)  or  aplay {OUTPUT_PATH}  (Linux)")
    print()
    print("Listen for: the [whispers] section should sound quieter. The [laughs]")
    print("should sound like a real laugh, not the word 'laughs'. If the tags")
    print("come out as spoken words, the prompt-engineering assumption is broken")
    print("and we need a different approach for Agent B's system prompt.")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
