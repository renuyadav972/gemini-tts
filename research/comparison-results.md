# Real Call Results — Internal Data

Phone calls via Plivo, Apr 16 2026. Same number, same ngrok tunnel, same LLM prompt space.

**Note:** Per the latest editorial direction, this head-to-head data is kept as internal test data for our records. The public-facing post is NOT framed as Agent A vs Agent B — the angle is "Google completed their voice stack with Flash TTS." The latency gap below is real but doesn't belong in the post.

## Side by Side

| | **Agent A — Native S2S** | **Agent B — Cascaded, fully Google** |
|---|---|---|
| Pipeline | Plivo → Gemini 3.1 Flash Live → Plivo | Plivo → Google STT (chirp_2) → Gemini 2.5 Flash → Gemini 3.1 Flash TTS → Plivo |
| Voice | Aoede (native to Flash Live) | Aoede (Flash TTS) |
| Call duration | ~90 s | Multiple calls, ~30–90 s each |
| Turns observed | 6 | 5–6 per call |
| **First-audio latency** | **556 ms** (one clean measurement) | **~2000 ms per turn** (STT 1200 + LLM 600 + TTS 650) |
| Audio tag support | emergent (not steerable) | explicit (`[apologetic]`, `[sighs]`, `[excited]`, etc.) |
| Multi-speaker | ❌ | ✅ (but voices less distinct than marketed) |
| Expressivity gotcha | — | LLM emitted `[apologetic] I'm sorry, I'm not able to express emotions` |

## The Headline Number

**Agent A is ~3.5× faster to first audio.**

- Agent A's native S2S: 556 ms TTFB
- Agent B's cascaded stack: ~2000 ms per turn (STT 1219 + LLM 611 + TTS 715 median)

For a live phone agent where responsiveness is the product, that's the gap that matters. Rhythm is everything — the user feels that ~1.5s delta.

## Caveat on the Agent A Metric

Gemini Live runs as a single persistent WebSocket. Pipecat's observer only emits one TTFB at connection setup because there's no discrete request-response per turn — turn-taking is managed inside Gemini's model, not by the pipeline. So 556 ms is the cleanest comparable number we have.

We can still compare user-experience turn latency manually from the bot-stopped → bot-started gaps minus user-speaking time, but that's subjective. The 556 ms figure matches the user's qualitative experience of Agent A "feeling fast."

## The Features Agent A Doesn't Have

1. **Explicit tone control.** Agent A cannot emit `[apologetic]` or `[excited]`. Its tone is emergent — whatever the model decides. That's fine for casual conversation, insufficient for scripted delivery.
2. **Multi-speaker.** Flash Live is one voice per session. Flash TTS handles two+ in one call.
3. **Voice identity per-turn.** Flash Live commits to one voice at session start. Flash TTS lets you switch voices across turns if you want.

## The Features Agent B Doesn't Have

1. **Low-latency turn-taking.** ~2s total TTFB is fine for scripted content, harsh for live conversation.
2. **Tone-hearing.** Agent B loses caller tone at the STT step.
3. **Inherent multilingual.** Even with chirp_2 STT configured for multiple languages, the cascaded path's multilingual behavior is weaker than native A2A (covered in `gemini-s2s`).
4. **A consistent sense of self.** LLM sometimes contradicts the TTS's capability ("I can't express emotion" while emitting `[apologetic]`). Native model doesn't have this split.

## The Routing Table

| If you need… | Pick |
|---|---|
| Live phone agent with natural turn-taking | Agent A (Flash Live) |
| Multilingual code-switching mid-utterance | Agent A (Flash Live) |
| Directorial control over tone per line | Agent B (cascaded Flash TTS) |
| Multi-speaker narration in one call | Agent B (cascaded Flash TTS) |
| Scripted / compliance / IVR delivery | Agent B (cascaded Flash TTS) |
| Same text, 30 voice choices × 70+ languages | Agent B (cascaded Flash TTS) |
| Fastest-to-first-audio from Google's stack | Agent A (Flash Live) |

Not a leaderboard. A routing decision.
