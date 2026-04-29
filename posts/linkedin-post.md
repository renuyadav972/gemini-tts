# LinkedIn Post. Gemini Flash TTS, tested

Google shipped Gemini Flash TTS — their first dedicated TTS, first-party, runs on Vertex AI alongside the rest of the model family. We wired it into a voice agent over Plivo telephony, ran real phone calls plus 30-run benchmarks, and pushed on every feature.

𝐎𝐧𝐞 𝐠𝐨𝐭𝐜𝐡𝐚 𝐮𝐩 𝐟𝐫𝐨𝐧𝐭: the 3.1 preview model needs Vertex AI API enabled, not just Cloud TTS. Without it, no streaming — you get the whole utterance at once. The older 2.5 Flash TTS runs on vanilla Cloud TTS; 3.1 routes through Vertex AI. Check this before you wire it up.

𝐖𝐡𝐚𝐭 𝐡𝐨𝐥𝐝𝐬:

• 𝐏𝐥𝐚𝐢𝐧 𝐭𝐞𝐱𝐭 𝐬𝐡𝐚𝐩𝐞𝐬 𝐩𝐫𝐨𝐬𝐨𝐝𝐲. The "apologetic" line softens. The "excited" one lifts. No tags, no SSML. The model reads emotional intent from the words themselves.

• 𝐈𝐧𝐥𝐢𝐧𝐞 𝐚𝐮𝐝𝐢𝐨 𝐭𝐚𝐠𝐬 𝐰𝐨𝐫𝐤. Write [whispers] inline and the voice actually whispers — mid-sentence, over 8 kHz μ-law phone audio. [laughs] is a real laugh, not the word. 5 of 6 tagged samples came back at 0.000 WER round-trip.

• 𝐃𝐢𝐫𝐞𝐜𝐭𝐨𝐫'𝐬 𝐍𝐨𝐭𝐞𝐬 𝐬𝐡𝐚𝐩𝐞𝐬 𝐝𝐞𝐥𝐢𝐯𝐞𝐫𝐲. Same voice, same line, four steps of prompt intensity — none → minor → major → extreme — pulled rendering from a flat read into deliberate, scene-specific delivery. The duration alone tracks the direction (4.1s → 10.2s). Direction is a real lever.

𝐖𝐡𝐚𝐭 𝐝𝐨𝐞𝐬𝐧'𝐭:

• 𝐃𝐢𝐬𝐟𝐥𝐮𝐞𝐧𝐜𝐢𝐞𝐬. We tried both documented approaches. Asking Director's Notes to add "um" and "hmm" — model just slowed pacing. Writing fillers into the transcript — model read "um" and "uh" as words with awkward pauses around them. Neither produced natural hesitation. If your voice agent needs human-sounding fillers, plan to engineer it yourself.

• 𝐌𝐮𝐥𝐭𝐢-𝐬𝐩𝐞𝐚𝐤𝐞𝐫. Three voice pairs (Puck+Kore, Fenrir+Leda, Charon+Leda) — all sounded like the same voice slightly modulating. Two-character dialog needs two separate calls.

𝐏𝐫𝐨𝐝𝐮𝐜𝐭𝐢𝐨𝐧 𝐧𝐮𝐦𝐛𝐞𝐫𝐬 (30 runs):

• First-chunk latency p50: 𝟔𝟗𝟔 𝐦𝐬 (p90 789, p99 1,122)
• Real-time factor: 𝟏.𝟔× (streams faster than playback)
• WER round-trip: 𝟐.𝟗% overall, 5 of 6 tag samples at 0.000

𝐖𝐡𝐞𝐫𝐞 𝐢𝐭 𝐟𝐢𝐭𝐬: 696 ms p50 is fine for scripted, IVR, outbound, and conversational personas where each turn is generated then played. Sub-300 ms real-time turn-taking is slower than you want today. Expressive when used right, with specific limits.

Dashboard with audio A/Bs: https://dashboard-gemini-tts.vercel.app
Repo: https://github.com/renuyadav972/gemini-tts
