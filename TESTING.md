# Testing — Gemini S2S vs Gemini TTS

Concrete steps to get both agents running on real phone calls.

## Prerequisites

- Python 3.11+
- A Plivo account with at least one phone number
- A Google AI Studio / Gemini API key (for the LLM + native Flash Live)
- A Google Cloud project with:
  - Cloud Text-to-Speech API enabled
  - A service account JSON with `roles/cloudtts.user`
  - (the `gemini-3.1-flash-tts-preview` model enabled — it's in preview so access may be gated)
- A Deepgram API key (Agent B only)
- [ngrok](https://ngrok.com) to expose the local server to Plivo

## 1. Install

```bash
cd /Users/renu/projects/gemini-tts
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# then fill in .env
```

## 2. Phase 0 — De-risk the TTS path (do this FIRST)

Before touching Pipecat or Plivo, verify the preview model actually streams via Cloud TTS:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/sa.json
python scripts/derisk_gemini_tts.py
```

This writes `derisk_output.wav`. Play it — the `[whispers]`/`[excited]`/`[laughs]` tags should render as actual vocal changes, not as spoken words. If they come out as spoken words, Agent B's system prompt needs a different approach.

The script also prints first-chunk latency, which is the lower bound for what Agent B can achieve over the phone.

## 3. Run Agent A (native Flash Live) on port 8001

Terminal 1 — ngrok:
```bash
ngrok http 8001
# note the HTTPS host, paste into .env as PUBLIC_DOMAIN
```

Terminal 2 — agent:
```bash
SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())") \
  python agent_native.py -t plivo -x $PUBLIC_DOMAIN --port 8001
```

Terminal 3 — place a call:
```bash
python scripts/make_call.py --to +91XXXXXXXXXX --ngrok https://$PUBLIC_DOMAIN --port 8001 --language en
```

## 4. Run Agent B (cascaded Google) on port 8000

Same shape, different port. Stop Agent A first (one ngrok tunnel at a time) or use a second ngrok profile.

```bash
SSL_CERT_FILE=$(python -c "import certifi; print(certifi.where())") \
  python agent_cascaded_google.py -t plivo -x $PUBLIC_DOMAIN --port 8000
```

```bash
python scripts/make_call.py --to +91XXXXXXXXXX --ngrok https://$PUBLIC_DOMAIN --port 8000
```

## 5. Metrics output

Each call writes a session JSON to `data/sessions/{session_id}.json` with the per-turn latency waterfall (STT → LLM → TTS TTFB), transcripts, and summary stats. The call recording MP3 lands in the same folder after Plivo finalizes it.

## 6. What to test (maps to research/test-plan.md)

Run both agents against the same set of scripted calls, back-to-back:

1. **Basic support dialog** — 5 turns, general knowledge questions. Measure TTFB, naturalness.
2. **Multilingual code-switch** — start English, mid-call switch to Spanish, mid-sentence switch to Hindi. Agent A handles this natively; Agent B depends on Deepgram + Gemini LLM + TTS all handling the mix.
3. **Expressive turn** — prompt the agent to apologize, then to celebrate. Listen for `[apologetic]` / `[excited]` rendering in Agent B's audio. Agent A's tone is emergent and should sound natural but uniform.
4. **Barge-in** — interrupt the agent mid-utterance. Time how long until it silences.
5. **Long-form** — a 30-second monologue from the caller. Tests STT stability (Agent B) vs. the native turn-taker (Agent A).

Recordings + session JSONs can then be imported into a dashboard (clone of https://dashboard-s2s.vercel.app/).

## Known gotchas

- **Auth is split for Agent B.** LLM uses `GOOGLE_API_KEY` (Gemini API), TTS uses `GOOGLE_APPLICATION_CREDENTIALS` (Cloud TTS service account). Both are required.
- **24 kHz → 8 kHz downsample.** Gemini TTS emits 24 kHz; Plivo needs 8 kHz. Pipecat resamples automatically, but audio-tag expressiveness may attenuate at 8 kHz μ-law. Listen carefully on Phase 0 vs. phone recording.
- **Preview model access.** `gemini-3.1-flash-tts-preview` may be gated per-project. If Phase 0 fails with a model-not-found error, request access via Google AI Studio or fall back temporarily to `gemini-2.5-flash-tts` to verify the rest of the pipeline.
- **Metrics observer attribution.** Already fixed in this repo's copy — `_classify_processor` checks `"tts"` before vendor keywords. The original `gemini-s2s` version would have misattributed Gemini TTS TTFB to LLM.
