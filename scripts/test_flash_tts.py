"""
Tier 1 empirical tests for Gemini 3.1 Flash TTS.

Runs three tests and writes JSON results + a compact markdown summary
to data/metrics/. These are the numbers that go into the post.

Tests
-----
1. Latency distribution
   30 runs of the same short prompt. Records first-chunk latency and
   total stream time. Computes p50 / p90 / p99 / mean / stdev.

2. WER round-trip
   For each of the six audio-tag samples (already rendered in
   data/samples/), feed the WAV to Google Cloud Speech-to-Text and
   compare the transcription to the original text with tags stripped.
   Word Error Rate quantifies intelligibility of the rendered audio.

3. Consistency
   Same input rendered 10 times. Measures variance in duration, byte
   count, and RMS energy. Tells you whether the model produces the
   same delivery twice or varies run-to-run.

Usage
-----
    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
    python scripts/test_flash_tts.py
"""

import io
import json
import math
import os
import re
import sys
import time
import wave
from pathlib import Path

from google.cloud import texttospeech_v1
from google.cloud import speech_v2
from jiwer import wer


MODEL = os.getenv("GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview")
VOICE = os.getenv("GEMINI_TTS_VOICE", "Aoede")

ROOT = Path(__file__).parent.parent
METRICS_DIR = ROOT / "data" / "metrics"
SAMPLES_DIR = ROOT / "data" / "samples"

LATENCY_ITERATIONS = 30
CONSISTENCY_ITERATIONS = 10

LATENCY_PROMPT = (
    "Hi there. I am a short test prompt used to measure latency. "
    "Please return audio quickly so we can benchmark you."
)

CONSISTENCY_PROMPT = (
    "[warm] Hello, thanks for calling. I can help with what you need today."
)

TAG_TESTS = [
    ("warm",       "[warm] Hello, thanks for calling. It's really nice to hear from you.",
                   "Hello, thanks for calling. It's really nice to hear from you."),
    ("excited",    "Guess what? [excited] Your package just arrived at the front door!",
                   "Guess what? Your package just arrived at the front door!"),
    ("apologetic", "[apologetic] I'm so sorry, that wait was much longer than it should have been.",
                   "I'm so sorry, that wait was much longer than it should have been."),
    ("whispers",   "Let me tell you something. [whispers] I don't usually share this with everyone.",
                   "Let me tell you something. I don't usually share this with everyone."),
    ("laughs",     "That's a good one. [laughs] I did not see that punchline coming.",
                   "That's a good one. I did not see that punchline coming."),
    ("sighs",      "[sighs] Alright, let me pull up your account and figure out what happened.",
                   "Alright, let me pull up your account and figure out what happened."),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _voice_params():
    return texttospeech_v1.VoiceSelectionParams(
        language_code="en-US", name=VOICE, model_name=MODEL,
    )


def _streaming_config():
    return texttospeech_v1.StreamingSynthesizeConfig(
        voice=_voice_params(),
        streaming_audio_config=texttospeech_v1.StreamingAudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.PCM,
            sample_rate_hertz=24000,
        ),
    )


def _request_generator(config_request, text):
    yield config_request
    yield texttospeech_v1.StreamingSynthesizeRequest(
        input=texttospeech_v1.StreamingSynthesisInput(text=text)
    )


def _stream_once(client, text):
    """Run a single streaming synthesis. Returns timing and PCM bytes."""
    cfg_req = texttospeech_v1.StreamingSynthesizeRequest(streaming_config=_streaming_config())
    t0 = time.perf_counter()
    first_chunk_at = None
    chunks = []
    for resp in client.streaming_synthesize(_request_generator(cfg_req, text)):
        if first_chunk_at is None:
            first_chunk_at = time.perf_counter()
        chunks.append(resp.audio_content)
    t_end = time.perf_counter()
    pcm = b"".join(chunks)
    return {
        "first_chunk_ms": round((first_chunk_at - t0) * 1000, 1) if first_chunk_at else None,
        "total_ms": round((t_end - t0) * 1000, 1),
        "chunks": len(chunks),
        "audio_bytes": len(pcm),
        "audio_duration_s": round(len(pcm) / (24000 * 2), 3),
        "pcm": pcm,
    }


def _stats(values):
    """p50 / p90 / p99 / mean / stdev / min / max for a list of numbers."""
    if not values:
        return {}
    sorted_v = sorted(values)
    n = len(sorted_v)
    mean = sum(sorted_v) / n
    var = sum((v - mean) ** 2 for v in sorted_v) / n
    def pct(p):
        k = (n - 1) * (p / 100)
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return round(sorted_v[int(k)], 1)
        return round(sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f), 1)
    return {
        "count": n,
        "min": round(sorted_v[0], 1),
        "p50": pct(50),
        "p90": pct(90),
        "p99": pct(99),
        "max": round(sorted_v[-1], 1),
        "mean": round(mean, 1),
        "stdev": round(math.sqrt(var), 1),
    }


# ---------------------------------------------------------------------------
# Test 1 — latency distribution
# ---------------------------------------------------------------------------


def test_latency(tts_client):
    print(f"[1/3] Latency distribution — {LATENCY_ITERATIONS} runs")
    runs = []
    for i in range(LATENCY_ITERATIONS):
        try:
            r = _stream_once(tts_client, LATENCY_PROMPT)
        except Exception as e:
            print(f"    run {i+1}: FAILED ({e})")
            continue
        runs.append({
            "iteration": i + 1,
            "first_chunk_ms": r["first_chunk_ms"],
            "total_ms": r["total_ms"],
            "chunks": r["chunks"],
            "audio_duration_s": r["audio_duration_s"],
            "real_time_factor": round(r["audio_duration_s"] / (r["total_ms"] / 1000), 2) if r["total_ms"] else None,
        })
        print(f"    run {i+1:2}: first_chunk={r['first_chunk_ms']:.0f}ms total={r['total_ms']:.0f}ms")

    first_chunks = [r["first_chunk_ms"] for r in runs if r["first_chunk_ms"]]
    totals = [r["total_ms"] for r in runs if r["total_ms"]]
    rtfs = [r["real_time_factor"] for r in runs if r["real_time_factor"]]

    return {
        "prompt": LATENCY_PROMPT,
        "iterations_requested": LATENCY_ITERATIONS,
        "iterations_successful": len(runs),
        "first_chunk_ms": _stats(first_chunks),
        "total_ms": _stats(totals),
        "real_time_factor": _stats(rtfs),
        "runs": runs,
    }


# ---------------------------------------------------------------------------
# Test 2 — WER round-trip on the six tag samples
# ---------------------------------------------------------------------------


STT_LOCATION = "us-central1"  # chirp_2 is region-pinned, not global


def _transcribe_pcm(stt_client, pcm_bytes, project_id):
    """Transcribe 24 kHz PCM audio using Cloud Speech-to-Text v2 with chirp_2."""
    config = speech_v2.RecognitionConfig(
        explicit_decoding_config=speech_v2.ExplicitDecodingConfig(
            encoding=speech_v2.ExplicitDecodingConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            audio_channel_count=1,
        ),
        language_codes=["en-US"],
        model="chirp_2",
    )
    request = speech_v2.RecognizeRequest(
        recognizer=f"projects/{project_id}/locations/{STT_LOCATION}/recognizers/_",
        config=config,
        content=pcm_bytes,
    )
    response = stt_client.recognize(request=request)
    return " ".join(r.alternatives[0].transcript for r in response.results if r.alternatives)


def _wav_to_pcm(wav_path):
    with wave.open(str(wav_path), "rb") as w:
        return w.readframes(w.getnframes())


def _strip_tags(text):
    return re.sub(r"\[[^\]]+\]", "", text).strip()


def test_wer(stt_client, project_id):
    print(f"[2/3] WER round-trip — {len(TAG_TESTS)} tag samples")
    per_tag = []
    all_refs = []
    all_hyps = []
    for tag_name, input_text, reference_text in TAG_TESTS:
        wav_path = SAMPLES_DIR / f"tag_{tag_name}.wav"
        if not wav_path.exists():
            print(f"    [{tag_name}] SKIP (missing {wav_path})")
            continue
        pcm = _wav_to_pcm(wav_path)
        try:
            hyp = _transcribe_pcm(stt_client, pcm, project_id)
        except Exception as e:
            print(f"    [{tag_name}] STT FAILED: {e}")
            continue
        w = wer(reference_text.lower(), hyp.lower())
        per_tag.append({
            "tag": tag_name,
            "reference": reference_text,
            "transcription": hyp,
            "wer": round(w, 4),
        })
        all_refs.append(reference_text.lower())
        all_hyps.append(hyp.lower())
        print(f"    [{tag_name:10}] wer={w:.3f}  hyp=\"{hyp}\"")

    overall = round(wer(all_refs, all_hyps), 4) if all_refs else None
    return {
        "overall_wer": overall,
        "per_tag": per_tag,
    }


# ---------------------------------------------------------------------------
# Test 3 — consistency
# ---------------------------------------------------------------------------


def _rms(pcm_bytes):
    """Mean RMS energy of 16-bit little-endian PCM. Returns a float in [0, 1]."""
    import struct
    n = len(pcm_bytes) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes)
    sq = sum(s * s for s in samples) / n
    return math.sqrt(sq) / 32768.0


def test_consistency(tts_client):
    print(f"[3/3] Consistency — {CONSISTENCY_ITERATIONS} runs, same input")
    runs = []
    for i in range(CONSISTENCY_ITERATIONS):
        try:
            r = _stream_once(tts_client, CONSISTENCY_PROMPT)
        except Exception as e:
            print(f"    run {i+1}: FAILED ({e})")
            continue
        runs.append({
            "iteration": i + 1,
            "first_chunk_ms": r["first_chunk_ms"],
            "audio_duration_s": r["audio_duration_s"],
            "audio_bytes": r["audio_bytes"],
            "rms_energy": round(_rms(r["pcm"]), 5),
        })
        print(f"    run {i+1:2}: duration={r['audio_duration_s']:.2f}s rms={runs[-1]['rms_energy']:.4f}")

    dur = [r["audio_duration_s"] for r in runs]
    rms = [r["rms_energy"] for r in runs]

    def cv(values):
        if not values:
            return None
        m = sum(values) / len(values)
        if m == 0:
            return 0.0
        var = sum((v - m) ** 2 for v in values) / len(values)
        return round(math.sqrt(var) / m, 4)

    return {
        "prompt": CONSISTENCY_PROMPT,
        "iterations_requested": CONSISTENCY_ITERATIONS,
        "iterations_successful": len(runs),
        "duration_s": {"stats": _stats(dur), "cv": cv(dur)},
        "rms_energy": {"stats": _stats(rms), "cv": cv(rms)},
        "runs": runs,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not creds or not os.path.exists(creds):
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS not set")
        sys.exit(1)

    # Extract project_id from service account JSON for STT v2 recognizer path.
    with open(creds) as f:
        project_id = json.load(f).get("project_id")
    if not project_id:
        print("ERROR: project_id missing from service account JSON")
        sys.exit(1)

    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Model:   {MODEL}")
    print(f"Voice:   {VOICE}")
    print(f"Project: {project_id}")
    print(f"Output:  {METRICS_DIR}\n")

    tts_client = texttospeech_v1.TextToSpeechClient()
    # STT v2 with chirp_2 requires the regional endpoint, not global.
    stt_client = speech_v2.SpeechClient(
        client_options={"api_endpoint": f"{STT_LOCATION}-speech.googleapis.com"}
    )

    # Run all three tests. Catch per-test errors so partial results still save.
    started = time.time()
    out = {
        "model": MODEL,
        "voice": VOICE,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tests": {},
    }

    try:
        out["tests"]["latency"] = test_latency(tts_client)
    except Exception as e:
        out["tests"]["latency"] = {"error": str(e)}
        print(f"latency test failed: {e}")

    print()
    try:
        out["tests"]["wer_roundtrip"] = test_wer(stt_client, project_id)
    except Exception as e:
        out["tests"]["wer_roundtrip"] = {"error": str(e)}
        print(f"wer test failed: {e}")

    print()
    try:
        out["tests"]["consistency"] = test_consistency(tts_client)
    except Exception as e:
        out["tests"]["consistency"] = {"error": str(e)}
        print(f"consistency test failed: {e}")

    elapsed = round(time.time() - started, 1)
    out["elapsed_s"] = elapsed

    # Persist
    json_path = METRICS_DIR / "flash_tts_tier1.json"
    with open(json_path, "w") as f:
        json.dump(out, f, indent=2)

    # Compact markdown summary
    md_lines = []
    md_lines.append("# Gemini 3.1 Flash TTS — Tier 1 empirical results\n")
    md_lines.append(f"Model: `{MODEL}`   Voice: `{VOICE}`   Generated: {out['generated_at']}\n")

    lat = out["tests"].get("latency", {})
    if "first_chunk_ms" in lat:
        s = lat["first_chunk_ms"]
        md_lines.append("## Latency distribution\n")
        md_lines.append(f"- Runs: {lat['iterations_successful']} / {lat['iterations_requested']}")
        md_lines.append(f"- First-chunk: p50 {s['p50']} ms, p90 {s['p90']} ms, p99 {s['p99']} ms, mean {s['mean']} ms, stdev {s['stdev']} ms")
        md_lines.append(f"- Range: {s['min']} to {s['max']} ms")
        rtf = lat.get("real_time_factor", {})
        if rtf:
            md_lines.append(f"- Real-time factor (audio_s / total_s): p50 {rtf['p50']}, mean {rtf['mean']}")
        md_lines.append("")

    werr = out["tests"].get("wer_roundtrip", {})
    if "per_tag" in werr:
        md_lines.append("## WER round-trip\n")
        md_lines.append(f"Overall WER across 6 tag samples: **{werr.get('overall_wer')}**\n")
        md_lines.append("| Tag | WER | Transcription |")
        md_lines.append("|---|---|---|")
        for row in werr["per_tag"]:
            md_lines.append(f"| {row['tag']} | {row['wer']} | {row['transcription']} |")
        md_lines.append("")

    cons = out["tests"].get("consistency", {})
    if "duration_s" in cons:
        md_lines.append("## Consistency\n")
        d = cons["duration_s"]
        r = cons["rms_energy"]
        md_lines.append(f"Same input rendered {cons['iterations_successful']} times:\n")
        md_lines.append(f"- Duration: {d['stats']['p50']} s (p50), cv = {d['cv']}")
        md_lines.append(f"- RMS energy: {r['stats']['p50']} (p50), cv = {r['cv']}")
        md_lines.append("")
        md_lines.append(f"Coefficient of variation < 0.05 means the model returns nearly identical output across runs. Higher values indicate run-to-run variation in delivery.\n")

    md_path = METRICS_DIR / "flash_tts_tier1.md"
    with open(md_path, "w") as f:
        f.write("\n".join(md_lines))

    print(f"\nDone in {elapsed}s.")
    print(f"  JSON: {json_path}")
    print(f"  MD:   {md_path}")


if __name__ == "__main__":
    main()
