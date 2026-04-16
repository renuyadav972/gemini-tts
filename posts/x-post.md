# X / Twitter Post. Gemini Flash TTS, tested

## Option A. Single tweet

Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.

First-chunk p50 696 ms though. 3 to 10x slower than ElevenLabs Flash or Cartesia for live turns.

## Option B. Thread (6 tweets)

**1/**
Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.

Wired it into a cascaded agent (Cloud STT + Gemini LLM + Flash TTS) over Plivo, plus 30 back-to-back runs of our own.

**2/**
One turn. Caller asked for 237 × 18. LLM wrote:

"[sighs] Yes, I can help with that. 237 times 18 is 4266."

Sigh is a real exhale. Math is right. Phone codec didn't flatten it.

**3/**
What we measured (30 runs + WER round-trip):

• First-chunk p50: 696 ms (p90 789, p99 1,122)
• WER round-trip: 2.9% overall, 5 of 6 samples at 0.000
• Duration CV: 0.029 (pacing near-identical run to run)
• Real-time factor: 1.6×

**4/**
What stood out:

Shifts are mid-sentence, not per-line. Voice drops to whisper, comes back up inside the same utterance.

[laughs] is a real laugh, not the word. Non-verbal sounds generated inline, no splices.

8 kHz phone codec didn't destroy it. That matters.

**5/**
What bit us:

Latency 696 ms p50. Slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms).

3.1 preview needs Vertex AI, not just Cloud TTS.

Multi-speaker: 3 voice pairs, all sounded like the same voice modulating.

**6/**
Google's cadence is the tell. Flash Live three weeks ago. Flash TTS this week. Both first-party.

Google knows neither wins alone. They're shipping both so builders route per turn, not per philosophy.

Dashboard: [URL]
Prior: https://github.com/renuyadav972/gemini-s2s

## Option C. Short single observation

Gemini 3.1 Flash TTS. Write [whispers] inline, voice actually whispers. Mid-sentence. Over phone audio.

Measured WER round-trip 2.9%, 5 of 6 tag samples letter-perfect. Latency p50 696 ms though. 3 to 10x slower than ElevenLabs Flash.
