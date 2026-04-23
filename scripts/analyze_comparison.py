"""
Compute per-provider voice quality metrics from data/comparison/*.wav.

Metrics:
  - duration (seconds) — length of generated audio
  - pause ratio (%) — fraction of audio below a quiet threshold
  - energy CV — coefficient of variation of windowed RMS

Run after scripts/compare_tts.py has produced WAVs. Assumes 24 kHz mono PCM16.

Usage:
    python scripts/analyze_comparison.py
"""

import json
import wave
from pathlib import Path

import numpy as np

COMPARISON_DIR = Path(__file__).parent.parent / "data" / "comparison"
PROVIDERS = ["gemini", "elevenlabs", "cartesia"]
SENTENCES = ["greeting", "excited", "apologetic", "quiet", "amused", "resigned"]

# RMS threshold below which a 20 ms window counts as a pause. -40 dBFS works
# well for clean TTS output; tune if your samples are noisier.
PAUSE_DB_THRESHOLD = -40.0
WINDOW_MS = 20


def read_pcm16(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        raw = w.readframes(n)
    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    return samples, sr


def rms_windows(samples: np.ndarray, sr: int, window_ms: int) -> np.ndarray:
    win = max(1, int(sr * window_ms / 1000))
    n_windows = len(samples) // win
    if n_windows == 0:
        return np.zeros(1)
    trimmed = samples[: n_windows * win].reshape(n_windows, win)
    return np.sqrt(np.mean(trimmed**2, axis=1) + 1e-12)


def pause_ratio(samples: np.ndarray, sr: int) -> float:
    rms = rms_windows(samples, sr, WINDOW_MS)
    db = 20 * np.log10(rms + 1e-12)
    return float(np.mean(db < PAUSE_DB_THRESHOLD))


def energy_cv(samples: np.ndarray, sr: int) -> float:
    rms = rms_windows(samples, sr, WINDOW_MS)
    voiced = rms[rms > 10 ** (PAUSE_DB_THRESHOLD / 20)]
    if len(voiced) < 2:
        return 0.0
    return float(np.std(voiced) / (np.mean(voiced) + 1e-12))


def analyze_provider(provider: str) -> dict:
    per_sentence = []
    for s in SENTENCES:
        path = COMPARISON_DIR / f"{provider}_{s}.wav"
        if not path.exists():
            print(f"  missing: {path.name}")
            continue
        samples, sr = read_pcm16(path)
        dur = len(samples) / sr
        per_sentence.append(
            {
                "sentence": s,
                "duration_s": round(dur, 2),
                "pause_ratio": round(pause_ratio(samples, sr), 3),
                "energy_cv": round(energy_cv(samples, sr), 3),
            }
        )
    if not per_sentence:
        return {"provider": provider, "error": "no samples"}

    durs = [r["duration_s"] for r in per_sentence]
    pauses = [r["pause_ratio"] for r in per_sentence]
    cvs = [r["energy_cv"] for r in per_sentence]

    return {
        "provider": provider,
        "per_sentence": per_sentence,
        "avg_duration_s": round(float(np.mean(durs)), 2),
        "avg_pause_ratio": round(float(np.mean(pauses)), 3),
        "pause_ratio_range": [round(min(pauses), 3), round(max(pauses), 3)],
        "avg_energy_cv": round(float(np.mean(cvs)), 3),
    }


def main() -> None:
    if not COMPARISON_DIR.exists():
        raise SystemExit(f"Run compare_tts.py first; {COMPARISON_DIR} not found")

    results = {}
    for p in PROVIDERS:
        print(f"\n{p}:")
        results[p] = analyze_provider(p)
        r = results[p]
        if "error" in r:
            print(f"  {r['error']}")
            continue
        for row in r["per_sentence"]:
            print(
                f"  {row['sentence']:12} dur {row['duration_s']:4.2f}s  "
                f"pause {row['pause_ratio']*100:4.1f}%  energyCV {row['energy_cv']:.3f}"
            )

    print("\n" + "=" * 60)
    print("SUMMARY (averaged across 6 sentences)")
    print("=" * 60)
    print(f"\n{'Provider':<12} {'Avg dur':>9} {'Avg pause':>11} {'Pause range':>15} {'Energy CV':>11}")
    print("-" * 60)
    for p in PROVIDERS:
        r = results[p]
        if "error" in r:
            continue
        rng = f"{r['pause_ratio_range'][0]*100:.0f}–{r['pause_ratio_range'][1]*100:.0f}%"
        print(
            f"{p:<12} {r['avg_duration_s']:>7.2f}s "
            f"{r['avg_pause_ratio']*100:>10.1f}% "
            f"{rng:>15} "
            f"{r['avg_energy_cv']:>11.3f}"
        )

    out = COMPARISON_DIR / "analysis.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
