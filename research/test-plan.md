# Test Plan — Gemini 3.1 Flash TTS, feature-focused

What we're actually testing: the features Google shipped with Flash TTS on April 15, 2026. Not multilingual code-switching (that's a Flash Live story, already covered in `gemini-s2s`).

## Phase 0 — DONE

- ✅ `gemini-3.1-flash-tts-preview` is streamable via Vertex AI + Cloud TTS
- ✅ 24 kHz PCM mono output as documented
- ✅ First-chunk latency characterized: ~1000 ms steady-state
- ✅ Audio tags (`[warm]`, `[whispers]`, `[laughs]`, etc.) render as real vocal expression over phone audio

## Phase 1 — Feature Demo Scripts

Each script outputs a shareable WAV. These double as post artifacts (you can embed the audio in the LinkedIn/X writeup).

### 1. Audio tag catalog
`scripts/demo_audio_tags.py`
One short WAV per tag: `[warm]`, `[excited]`, `[apologetic]`, `[whispers]`, `[laughs]`, `[sighs]`. Same voice (Aoede), neutral carrier sentence, the tag in the middle so the contrast is audible. Answers: does every tag in the catalog actually do something distinguishable?

### 2. Prose-style direction
Inline in the system prompt OR in the TTS `prompt` parameter. Try "say this cheerfully: ...", "whisper this like a secret: ...". Compares against the bracket-tag approach — is prose-level direction easier/harder/better?

### 3. Native multi-speaker (the feature Flash Live literally cannot do)
`scripts/demo_multi_speaker.py`
A scripted dialogue between two speakers in ONE streaming API call. Alex = Puck, Riley = Kore. Answers: does multi-speaker actually work? Do the two voices sound distinct and paced naturally? This is the headline feature for "cascaded-Google-TTS does something native-S2S can't."

### 4. Voice consistency across languages
Same voice (Kore), same scripted character, one line in English, one in Spanish, one in French. Does the voice identity hold? This is what "70+ languages" means for this model — NOT code-switching, voice-identity preservation.

### 5. Naturalness A/B (later)
Blind listening test: Flash Live's native voice vs Flash TTS's `[warm] Aoede` voice, same line, phone audio. Which sounds better to 10+ listeners? Tests the Elo 1,211 claim at 8 kHz μ-law.

## Phase 2 — Live Phone Agent (Agent B)

Agent B remains the cascaded "fully Google" pipeline:
```
Plivo → Google STT (chirp_2, EN) → Gemini 2.5 Flash LLM → Gemini 3.1 Flash TTS → Plivo
```

The live agent is where we measure:
- End-to-end turn latency on real phone audio
- Expressivity through the LLM (strong prompt overrides "I'm just an AI" refusal)
- Barge-in / interruption behavior
- Real-world naturalness vs robotic feel

Not tested on the live agent (covered by demo scripts instead):
- Multi-speaker (it's a narration feature, not a turn-taking feature)
- Mid-call language switching (Flash Live story, not Flash TTS)

## Metrics that matter for THIS writeup

| Metric | Agent A target | Agent B target |
|---|---|---|
| TTFB per turn (phone) | ~400–500 ms | ~2000 ms (STT + LLM + TTS stack) |
| TTS expressivity rate | (emergent) | % of applicable turns that emit an audio tag |
| Multi-speaker capability | — | yes, one call, two voices |
| Voice identity across languages | 1 voice (Aoede) | 30 voices, 70+ languages |
| Naturalness (MOS-lite) | TBD | TBD |

## Known issues / caveats

1. **LLM refusal gap** — Gemini 2.5 Flash's RLHF defaults to "I can't express emotion" even when emitting the tag. Mitigated with a strong system prompt that explicitly overrides the reflex. Prior run log: the LLM wrote `[apologetic] I'm sorry, I'm not able to express emotions` — using the tag while denying the capability. Worth keeping as an anecdote in the writeup.
2. **Cascaded STT friction** — every STT choice has trade-offs. Google STT has worse Hindi out-of-the-box than Deepgram. Not relevant to this writeup since we're English-only.
3. **Session JSON observer flush** — currently broken in Pipecat 1.0.0, only MP3 is persisting. Need to fix if we want clean metrics exports. Fallback: parse `/tmp/agent_b.log` and extract turn data by regex.
4. **Vertex AI requirement** — `gemini-3.1-flash-tts-preview` requires Vertex AI API enabled (not just Cloud TTS). Older `gemini-2.5-flash-tts` goes through vanilla Cloud TTS. Interesting friction data point for the writeup.
