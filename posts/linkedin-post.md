# LinkedIn Post. Gemini Flash TTS, tested

Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.

"[sighs] Yes, I can help with that. 237 times 18 is 4266."

The sigh is a real exhale. Math is right. Phone codec didn't flatten it.

𝐖𝐡𝐚𝐭 𝐰𝐞 𝐦𝐞𝐚𝐬𝐮𝐫𝐞𝐝:

• First-chunk latency p50: 𝟔𝟗𝟔 𝐦𝐬 (30 runs; p90 789 ms, p99 1,122 ms)
• Intelligibility round-trip: 𝟐.𝟗% 𝐖𝐄𝐑, 5 of 6 tag samples at 0.000
• Real-time factor: 𝟏.𝟔× (streams faster than playback)
• Naturalness: Elo 𝟏,𝟐𝟏𝟏 on Artificial Analysis (Google's claim, blind human preference; we did not run our own)

𝐖𝐡𝐚𝐭 𝐬𝐭𝐨𝐨𝐝 𝐨𝐮𝐭:

Shifts are mid-sentence, not per-line. The voice drops to a whisper and comes back up inside the same utterance. SSML never got this right.

[laughs] is a real laugh, not the word. Same for [sighs]. The model generates the non-verbal sound inline, no pre-recorded splices.

The 8 kHz codec usually destroys prosody nuance. Here it didn't. That matters because phone audio is where most voice agents actually live.

𝐖𝐡𝐚𝐭 𝐛𝐢𝐭 𝐮𝐬:

Latency. 696 ms p50 is 3 to 10 times slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms). Fine for scripted, too slow for real-time turns.

Auth. The 3.1 preview needs Vertex AI API enabled, not just Cloud TTS. The 2.5 version runs on vanilla Cloud TTS.

Multi-speaker. Tested Puck+Kore, Fenrir+Leda, Charon+Leda. All three pairs sounded like the same voice slightly modulating.
Google's release cadence is the tell. Flash Live three weeks ago. Flash TTS this week. Both first-party. Google knows neither wins alone. They're shipping both so builders route per turn, not per philosophy.

Dashboard with charts, audio samples, and raw data: https://dashboard-tts.vercel.app
Prior work: https://github.com/renuyadav972/gemini-s2s
