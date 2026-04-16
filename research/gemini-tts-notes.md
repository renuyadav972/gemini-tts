# Gemini 3.1 Flash TTS — Research Notes

Released **April 15, 2026**. Dedicated text-to-speech model, now in preview.

## Phase 0 validation (local, Apr 16, 2026)

Standalone Cloud TTS `streaming_synthesize` run against `gemini-3.1-flash-tts-preview`, 5 runs, same 205-char input with `[warm]`, `[excited]`, `[whispers]`, `[laughs]` tags:

| Metric | Result |
|---|---|
| Model accessible | ✅ via Vertex AI (requires Vertex AI API enabled) |
| Streaming | ✅ real — 330–355 chunks per utterance, not a blob |
| Audio tags | ✅ render as vocal expression, NOT spoken words |
| Output | 24 kHz PCM s16le mono as documented |
| First-chunk latency | **~1000 ms steady-state** (1001 / 1019 / 1051 / 1057 ms; one 2130 ms outlier) |
| Total stream time | ~8.1–9.1s for ~14s of audio (faster than real-time) |

**Auth surprise:** `gemini-3.1-flash-tts-preview` is NOT served by vanilla Cloud TTS — it requires the **Vertex AI API** (`aiplatform.googleapis.com`) enabled on the same project, even when using the `google-cloud-texttospeech` client. The older `gemini-2.5-flash-tts` is on vanilla Cloud TTS.

**Implication for builders:** personal / small-team projects that don't want to touch Vertex AI are stuck on 2.5 for streaming. 3.1 preview is Vertex-gated.

## Model IDs

- `gemini-3.1-flash-tts-preview` (current, recommended)
- Older: `gemini-2.5-flash-preview-tts`, `gemini-2.5-pro-preview-tts`

## Availability

- Gemini API + Google AI Studio (preview)
- Vertex AI (enterprise)
- Google Vids (Workspace)

## Input / Output

| | |
|---|---|
| Input | Text, up to **16K tokens** |
| Output | Audio, up to **32K tokens** |
| Encoding | PCM, s16le, 16-bit |
| Sample rate | **24,000 Hz** |
| Channels | Mono |
| Watermarking | **SynthID** on all audio |
| Streaming | **Depends on API surface** — see below |

## Streaming — the nuance

Streaming support depends on which API you call:

| API surface | Streaming |
|---|---|
| Gemini API (`ai.google.dev`, `generate_content`) | ❌ No. Full utterance returned as one blob. Docs explicitly say *"TTS does not support streaming."* |
| Vertex AI API | ✅ Unidirectional — one text request → stream of audio chunks back |
| Cloud Text-to-Speech API (`streaming_synthesize`) | ✅ Bidirectional — multiple requests / multiple responses |

**Implication:** Flash TTS *is* viable for real-time voice agents, as long as you use Vertex AI or Cloud TTS, not the Gemini API. For this repo's cascaded agent we'll use the Cloud TTS `streaming_synthesize` path.

## Voices (30 prebuilt)

Zephyr, Puck, Charon, Kore, Fenrir, Leda, Orus, Aoede, Callirrhoe, Autonoe, Enceladus, Iapetus, Umbriel, Algieba, Despina, Erinome, Algenib, Rasalgethi, Laomedeia, Achernar, Alnilam, Schedar, Gacrux, Pulcherrima, Achird, Zubenelgenubi, Vindemiatrix, Sadachbia, Sadaltager, Sulafat.

## Languages (70+)

Arabic, English, French, German, Hindi, Japanese, Korean, Spanish, Portuguese, Russian, Mandarin, Traditional Chinese, Vietnamese, Thai, Filipino + 55 more (including regional variants).

## Audio Tags (200+)

Inline, bracket-style commands you can embed in prompts to steer delivery:

- Emotion: `[excited]`, `[sarcastic]`, `[tired]`, `[crying]`, `[admiration]`, `[anger]`, `[confusion]`, `[fear]`
- Action: `[whispers]`, `[shouting]`, `[sighs]`, `[laughs]`, `[gasps]`
- ~200 total modifiers

Also supports **natural-language style control** (e.g. "Say cheerfully: ...", "read this like a tired barista at 5am").

## Multi-Speaker (native)

Single API call can produce multi-voice dialogue — no stitching, pacing stays coherent. Configured via `MultiSpeakerVoiceConfig` mapping speaker labels to voice names.

```python
speech_config=types.SpeechConfig(
  multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
    speaker_voice_configs=[
      types.SpeakerVoiceConfig(speaker='Joe',  voice_config=...(voice_name='Puck')),
      types.SpeakerVoiceConfig(speaker='Jane', voice_config=...(voice_name='Kore')),
    ]
  )
)
```

## Benchmarks

- **Artificial Analysis TTS leaderboard: Elo 1,211** (blind human preference).

## Pricing

Not announced at launch.

## API (single speaker, minimal)

```python
response = client.models.generate_content(
  model="gemini-3.1-flash-tts-preview",
  contents="Say cheerfully: Have a wonderful day!",
  config=types.GenerateContentConfig(
    response_modalities=["AUDIO"],
    speech_config=types.SpeechConfig(
      voice_config=types.VoiceConfig(
        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Kore')
      )
    )
  )
)
```

REST: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-tts-preview:generateContent`

## Key Implications for Voice Agents

1. **Streaming works on Vertex / Cloud TTS, not on the Gemini API.** If your tutorial or starter code is pointed at `generate_content`, you'll feel like it's blocking — because it is. Switch to `streaming_synthesize` on Cloud TTS for real-time use.
2. **Audio tags are a superset of SSML** in practice — more expressive, natural language friendly, no XML.
3. **Multi-speaker native** means IVR / narration / onboarding-content workflows get dramatically simpler.
4. **SynthID watermark everywhere** — mandatory, can't opt out. Downstream detection implications.

## Sources

- [Google Blog — Gemini 3.1 Flash TTS announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-1-flash-tts/)
- [DeepMind model card — Gemini 3.1 Flash Audio](https://deepmind.google/models/model-cards/gemini-3-1-flash-audio/)
- [Gemini API docs — Speech generation](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Gemini API model list](https://ai.google.dev/gemini-api/docs/models)
- [Simon Willison — Gemini 3.1 Flash TTS](https://simonwillison.net/2026/Apr/15/gemini-31-flash-tts/)
- [MarkTechPost — new benchmark in expressive AI voice](https://www.marktechpost.com/2026/04/15/google-ai-launches-gemini-3-1-flash-tts-a-new-benchmark-in-expressive-and-controllable-ai-voice/)
- [Google Workspace blog — Vids voiceovers](https://workspaceupdates.googleblog.com/2026/04/new-more-expressive-ai-voiceovers-in-Google-Vids-and-16-additional-languages-powered-by-Gemini-3.1-Flash-TTS.html)
