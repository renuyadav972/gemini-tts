# Gemini 3.1 Flash Live vs. Gemini 3.1 Flash TTS — Head-to-Head

Three weeks apart, same family, both now streamable. That makes a real comparison possible.

## Phase 0 data (Apr 16, 2026)

Local de-risk run on `gemini-3.1-flash-tts-preview` (see `gemini-tts-notes.md` for full table):

- First-chunk latency: **~1000 ms steady-state** (5-run median)
- Audio tags (`[whispers]`, `[laughs]`, `[excited]`, `[warm]`) render as vocal expression, not spoken words — Agent B's prompt strategy is validated
- `gemini-3.1-flash-tts-preview` requires **Vertex AI API** enabled — vanilla Cloud TTS only serves 2.5

**Projected Agent B TTFB on phone calls:**
STT (~300ms) + LLM first token (~400ms) + TTS first chunk (~1000ms) = **~1.7s**
vs. Agent A native: **~400–500ms** typical.

That gap is the central number the writeup will turn on.

## Timeline

- **March 26, 2026** — Gemini 3.1 Flash Live globalizes Search Live to 200+ countries.
- **April 15, 2026** — Gemini 3.1 Flash TTS ships as a separate model with streaming via Vertex AI and Cloud TTS.

Both models stream. Both cover 70–90+ languages. Both come out of Google DeepMind. For the first time you can build a voice agent two ways on a fully-Google stack and actually measure which one wins.

## Side by Side

| Dimension | Flash **Live** | Flash **TTS** |
|---|---|---|
| Model ID | `gemini-3.1-flash-live-preview` | `gemini-3.1-flash-tts-preview` |
| Pipeline | Audio-to-audio (A2A) | Text-to-audio |
| Input | audio, video, images, text (128K) | text only (16K) |
| Output | audio + text (64K) | audio (32K) |
| Streaming | ✅ native Live API, bidirectional | ✅ Vertex AI (unidirectional), Cloud TTS (bidirectional); ❌ Gemini API |
| Languages | 90+ (inherent multilingual, mid-utterance code-switching) | 70+ prebuilt |
| Voice control | implicit — hears caller tone, matches in response | explicit — 200+ audio tags + natural-language direction |
| Voices | limited prebuilt set, expressive | 30 prebuilt (Puck, Kore, Zephyr, ...) |
| Multi-speaker | single voice out, conversational | **native multi-speaker in one call** |
| Hears caller tone | ✅ yes — it's A2A | ❌ no — it never touches caller audio |
| Best for | live conversation | narration + any pipeline where the LLM drafts text first |

## The Real Question for Builders

Before April 15, Google had a native S2S model and no strong first-party TTS. If you wanted a cascaded pipeline you reached for Deepgram + Gemini + ElevenLabs (see [gemini-s2s](https://github.com/renuyadav972/gemini-s2s)).

Now there's a second Google-only path:

```
Cascaded, fully Google:
Plivo ─▶ Deepgram STT ─▶ Gemini LLM ─▶ Gemini 3.1 Flash TTS (Cloud TTS stream) ─▶ Plivo

vs.

Native, fully Google:
Plivo ─▶ Gemini 3.1 Flash Live (A2A) ─▶ Plivo
```

Same provider. Same auth. Same billing. Two philosophies. Which one wins depends on what the agent has to do.

## What Each Approach Buys You — validated findings

Not "where each wins" — neither is going to be the universal answer. This is what each path gets you *that the other can't*, grounded in what we actually measured.

**Flash Live buys you:**
- **Tone-hearing.** The model hears *how* the caller said something, not just what. Cascaded loses this at the STT step.
- **Mid-sentence multilingual code-switching** without configuration. Inherent to A2A. (Covered in detail in the prior `gemini-s2s` writeup.)
- **Fewer moving parts on the hot path** — no STT → LLM → TTS stack to coordinate.
- **Faster first-audio.** Agent A typically ~400–500ms. Agent B lands at ~2s total TTFB per turn.

**Flash TTS buys you:**
- **Audio tag expressivity — the headline feature, validated.** We rendered `[warm]`, `[excited]`, `[apologetic]`, `[whispers]`, `[laughs]`, `[sighs]` as isolated WAVs and on live phone calls. All six audible, all six distinguishable, all six survive 8 kHz μ-law phone compression. This is a real upgrade over SSML-era "expressivity."
- **Inline, mid-sentence tag placement.** `"Let me tell you something. [whispers] I don't usually share this."` → voice drops to whisper mid-sentence, then shifts back.
- **Exact voice identity.** Pick a voice from 30 options; it holds across all tag modifiers and across languages.
- **Swap-ability.** Three pluggable layers instead of one black box.

**Both paths buy you**, now that both are Google: a single bill, a single auth surface, the SynthID watermark story, and the same preview-stage velocity of updates.

## Findings that qualify the TTS picture

1. **~1000 ms first-chunk latency.** Steady-state across 5+ standalone runs and confirmed on phone calls. For context: ElevenLabs Flash ~300–500 ms, Cartesia ~150–300 ms. Flash TTS is slower on the front edge — real cost for interactive use.
2. **LLM self-contradiction gap.** Gemini 2.5 Flash emitted `[apologetic] I'm sorry, I'm not able to express emotions` — using the tag correctly while denying the capability verbally. Cascaded has a seam native A2A doesn't have. Mitigable with aggressive system prompt but structurally fragile.
3. **3.1 preview is Vertex-gated.** The streamable newest Flash TTS requires Vertex AI API enabled. The older 2.5 goes through vanilla Cloud TTS. Real friction for small-team/personal projects.
4. **Multi-speaker voices less distinct than marketed.** Tested Puck+Kore and Fenrir+Leda in multi-speaker dialogue calls. Both sound closer than the "two distinct voices, one call" framing implied. Real feature, but not the dramatic voice-casting tool the announcement suggested. Demoted to footnote, not headline.

## The Honest Framing

This is the same trade-off the `gemini-s2s` post landed on — native vs. cascaded, swappable vs. coherent, emergent tone vs. specified tone — just sharper, because the vendor noise is gone. When both sides are Google, the only thing left to compare is the philosophy.

Which means the right answer for most real products is going to be **both, routed per turn**. Live for conversational turns where tone matters. TTS for scripted turns where delivery must match exact intent. The test below quantifies the trade-off so that routing has numbers behind it — not so one side wins.

## What a Head-to-Head Test Actually Measures

With both streamable, the measurements line up cleanly:

1. **Time-to-first-audio-byte** from caller speech end. Live's advantage: no STT step. TTS's advantage: smaller model per step, and Cloud TTS streaming is optimized for low-latency generation.
2. **Naturalness (blind A/B).** Does A2A prosody actually beat a directed TTS with audio tags? Open question — Flash TTS scored Elo 1,211 on the Artificial Analysis leaderboard.
3. **Multilingual behavior.** Live code-switches mid-sentence. Can the cascaded path match that if the LLM emits mixed-language text?
4. **Expressivity control.** Live's tone is emergent. TTS's tone is specified. Which matters more for your use case is an empirical question, not a dogmatic one.
5. **Cost per turn** — TBD until Flash TTS pricing lands. Cascaded likely has more moving pieces to bill.
6. **Failure modes.** A2A fails as one black box. Cascaded fails at one layer you can swap. Operational trade-off, not a quality one.

## What Google's Positioning Suggests

The DeepMind model card draws the line itself:

> **Flash Live** enables low-latency, real-time voice and video interactions — continuous streams of audio, video, or text to deliver immediate, human-like spoken responses.
>
> **Flash TTS** is a text-to-speech model, offering enhanced control, expressiveness, and audio quality for next-gen AI speech applications.

But Google also gave TTS a streaming surface. If TTS were purely for offline production, they wouldn't have. So the real design-intent split is:

- **Live = conversation where tone is two-way.**
- **TTS = any audio output where the LLM's text is the source of truth** — whether that's a podcast script or a live agent's next turn.

Flash TTS in a live agent isn't the wrong tool. It's the cascaded tool from a single vendor, finally first-party.

## What This Changes for the Build-vs-Integrate Conversation

A year ago the debate was "native S2S vs. cascaded STT + LLM + TTS" — and cascaded usually meant crossing vendor lines. Now Google covers both paths end to end.

The debate doesn't collapse into a winner. It clarifies: pick per turn, not per product.
