# Gemini 3.1 Flash TTS — tested

Write `[whispers]` inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.

We wired Google's new TTS preview into a cascaded voice agent (Cloud STT + Gemini LLM + Flash TTS), ran real phone calls through Plivo, and then ran an empirical test suite against the model.

**Live dashboard with audio samples and charts:** [dashboard link]

## What we measured

| Metric | Result |
|---|---|
| First-chunk latency p50 (30 runs) | **696 ms** (p90 789 ms, p99 1,122 ms) |
| Intelligibility round-trip (WER) | **2.9%** overall, 5 of 6 tag samples at 0.000 |
| Real-time factor | 1.6x (streams faster than playback) |
| Naturalness (Google's claim) | Elo 1,211 on Artificial Analysis |

## What stood out

- **Shifts are mid-sentence, not per-line.** The voice drops to a whisper and comes back up inside the same utterance. SSML never got this right.
- **[laughs] is a real laugh, not the word.** Same for [sighs]. The model generates the non-verbal sound inline, no pre-recorded splices.
- **The 8 kHz codec usually destroys prosody nuance.** Here it didn't. That matters because phone audio is where most voice agents actually live.

## What bit us

| Area | Finding |
|---|---|
| Latency | 696 ms p50 is 3 to 10 times slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms). Fine for scripted, too slow for real-time turns. |
| Auth | The 3.1 preview needs Vertex AI API enabled, not just Cloud TTS. |
| Multi-speaker | Tested Puck+Kore, Fenrir+Leda, Charon+Leda. All three pairs sounded like the same voice slightly modulating. |

## Repo layout

```
agent_native.py              Agent A: Gemini 3.1 Flash Live (native S2S, baseline)
agent_cascaded_google.py     Agent B: Cloud STT + Gemini LLM + Flash TTS (cascaded)
metrics_observer.py          Per-turn latency waterfall capture
scripts/
  derisk_gemini_tts.py       Phase 0: standalone streaming smoke test
  demo_audio_tags.py         Generate per-tag WAV samples
  demo_multi_speaker.py      Two-voice dialogue in one API call
  demo_voices.py             Voice catalog sampler
  test_flash_tts.py          Tier 1 empirical tests (latency, WER, consistency)
  make_call.py               Outbound Plivo test call
dashboard/
  index.html                 Live dashboard with Plivo branding
  samples/                   Audio samples (WAV)
data/
  metrics/                   Raw JSON + markdown test results
research/                    Internal notes, comparison docs, test plan
posts/                       LinkedIn + X post drafts (markdown)
```

## Quick start

```bash
git clone https://github.com/renuyadav972/gemini-tts.git
cd gemini-tts
python -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env
# Fill in GOOGLE_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, DEEPGRAM_API_KEY, Plivo creds
```

### Run the de-risk test (confirm model works)

```bash
python scripts/derisk_gemini_tts.py
```

### Run the empirical test suite

```bash
python scripts/test_flash_tts.py
```

### Run Agent B on a phone call

```bash
python agent_cascaded_google.py -t plivo -x <ngrok-host> --port 8000
python scripts/make_call.py --to +1XXXXXXXXXX --ngrok https://<ngrok-host> --port 8000
```

## Prerequisites

- Python 3.11+
- Google Cloud project with Cloud Text-to-Speech, Vertex AI, and Cloud Speech-to-Text APIs enabled
- Service account JSON with appropriate roles
- Plivo account with a phone number
- Deepgram API key (only if running the Deepgram STT variant)
- ngrok for exposing the local server to Plivo

## Prior work

[gemini-s2s](https://github.com/renuyadav972/gemini-s2s): Native Gemini Live (S2S) vs cross-vendor cascaded pipeline over real phone calls. Dashboard: [dashboard-s2s.vercel.app](https://dashboard-s2s.vercel.app/)
