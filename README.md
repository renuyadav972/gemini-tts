# Gemini 3.1 Flash TTS — Tested

Empirical test of Google's Gemini 3.1 Flash TTS Preview, run over real phone calls via Plivo and a 30-run benchmark suite.

- **Cascaded agent**: Google Cloud STT (chirp_2) → Gemini 2.5 Flash LLM → Gemini 3.1 Flash TTS, all first-party Google.
- **Baseline**: Gemini 3.1 Flash Live (native S2S) from [gemini-s2s](https://github.com/renuyadav972/gemini-s2s).

Live dashboard with audio samples, charts, and raw data: https://dashboard-gemini-tts.vercel.app

## How It Works

```
Cascaded (fully Google)
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐     ┌─────────────┐
│  Phone  │────▶│  Plivo  │────▶│  Google  │────▶│ Gemini │────▶│ Gemini 3.1  │
│  Call   │◀────│   WS    │◀────│   STT    │     │  LLM   │     │  Flash TTS  │
└─────────┘     └─────────┘     └──────────┘     └────────┘     └─────────────┘
```

Runs on Pipecat with Plivo's bidirectional WebSocket transport. The LLM's system prompt teaches it to emit audio tags like `[whispers]`, `[laughs]`, `[apologetic]` which the TTS renders as real vocal expression.

## Project Layout

```
agent_cascaded_google.py     Cascaded: Cloud STT + Gemini LLM + Flash TTS
agent_native.py              Baseline: Gemini 3.1 Flash Live (native S2S)
metrics_observer.py          Per-turn latency waterfall capture
scripts/
  derisk_gemini_tts.py       Standalone streaming smoke test
  test_flash_tts.py          Tier 1 empirical tests (latency, WER, consistency)
  demo_audio_tags.py         Generate per-tag WAV samples
  demo_multi_speaker.py      Two-voice dialogue in one API call
  demo_voices.py             Voice catalog sampler
  make_call.py               Outbound Plivo test call
dashboard/                   Live dashboard with audio samples and charts
data/metrics/                Raw JSON + markdown test results
```

## Prerequisites

- Python 3.11+
- A [Plivo](https://www.plivo.com/) account with a phone number
- A Google Gemini API key
- A Google Cloud project with Cloud Text-to-Speech, Vertex AI, and Cloud Speech-to-Text APIs enabled
- A service account JSON with appropriate roles
- [ngrok](https://ngrok.com/) to expose the local server to Plivo

## Quick Start

1. **Clone and install**
   ```bash
   git clone https://github.com/renuyadav972/gemini-tts.git
   cd gemini-tts
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Fill in your Plivo, Google API, service account, and Deepgram credentials.

3. **Run the de-risk test** (confirm model works before touching phone calls)
   ```bash
   python scripts/derisk_gemini_tts.py
   ```

4. **Run the empirical test suite**
   ```bash
   python scripts/test_flash_tts.py
   ```

5. **Run the agent on a phone call**
   ```bash
   ngrok http 8000
   ```
   Put the ngrok HTTPS host into `.env` as `PUBLIC_DOMAIN`, then:
   ```bash
   python agent_cascaded_google.py -t plivo -x <ngrok-host> --port 8000
   python scripts/make_call.py --to +1XXXXXXXXXX --ngrok https://<ngrok-host> --port 8000
   ```

## What We Found

A few things stood out from running the TTS through phone audio and a 30-run benchmark:

- **Audio tags work mid-sentence.** Write `[whispers]` inline and the voice drops to a whisper, then comes back up, inside the same utterance. `[laughs]` is a real laugh, not the word. SSML never got this right.
- **Phone codec survival.** 8 kHz μ-law usually destroys prosody nuance. The whisper stayed a whisper at 8 kHz. That matters because phone audio is where most voice agents actually live.
- **Latency.** First-chunk p50 is 696 ms across 30 runs (p90 789 ms). Slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms). Fine for scripted audio, too slow for real-time turns.
- **Intelligibility.** Round-trip WER of 2.9%. Five of six tag samples transcribed back letter-perfect. Audio tags did not degrade intelligibility.
- **Multi-speaker.** Tested three voice pairs. The two speakers sounded like the same voice slightly modulating.
- **Auth friction.** The 3.1 preview needs Vertex AI API enabled, not just Cloud TTS. Three API enables for one model.

Full writeup with audio samples: https://dashboard-gemini-tts.vercel.app

## License

MIT
