# Gemini 3.1 Flash TTS — Tier 1 empirical results

Model: `gemini-3.1-flash-tts-preview`   Voice: `Aoede`   Generated: 2026-04-16T18:57:30Z

## Latency distribution

- Runs: 30 / 30
- First-chunk: p50 695.5 ms, p90 788.5 ms, p99 1121.7 ms, mean 730.5 ms, stdev 105.4 ms
- Range: 647.0 to 1246.4 ms
- Real-time factor (audio_s / total_s): p50 1.6, mean 1.6

## WER round-trip

Overall WER across 6 tag samples: **None**

| Tag | WER | Transcription |
|---|---|---|

## Consistency

Same input rendered 10 times:

- Duration: 4.0 s (p50), cv = 0.0285
- RMS energy: 0.1 (p50), cv = 0.1065

Coefficient of variation < 0.05 means the model returns nearly identical output across runs. Higher values indicate run-to-run variation in delivery.
