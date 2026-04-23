# LinkedIn Post. Gemini Flash TTS, tested

Google shipped Gemini Flash TTS this week. We ran the same six sentences through it, ElevenLabs Flash v2.5, and Cartesia Sonic 3 — best conversational voice from each provider, no audio tags, plain text — to see where it actually lands on features and quality.

One thing worth flagging early: the 3.1 preview model needs Vertex AI API enabled, not just Cloud TTS. Without Vertex AI, the model doesn't stream. The older 2.5 Flash TTS runs on vanilla Cloud TTS, but the new 3.1 preview routes through Vertex AI for streaming synthesis.

𝐆𝐞𝐦𝐢𝐧𝐢 𝐩𝐚𝐜𝐞𝐬 𝐬𝐥𝐨𝐰𝐞𝐫 𝐚𝐧𝐝 𝐩𝐚𝐮𝐬𝐞𝐬 𝐦𝐨𝐫𝐞. The expressiveness story is more nuanced.

On the same six sentences, Gemini (Aoede) averages 4.29s per utterance — about 45% longer than Alexandra (2.92s) or Katie (2.99s). Most of the extra time is pause: Gemini spends 29% of each utterance in pauses, Cartesia 28%, ElevenLabs 24%. The "breathing room" observation holds — Gemini leaves more of it — but the gap with the other providers is narrower than it looked with default voices.

On energy variation, ElevenLabs Alexandra actually leads (CV 0.76). Cartesia Katie (0.61) and Gemini (0.60) trail. We first ran this with each provider's generic default voice and came away thinking ElevenLabs was flat and Cartesia was erratic. Swapping to each vendor's recommended conversational agent voice flipped both reads: Alexandra is dynamic, Katie's pause range is 22–40% (vs Jacqueline's 0–47% swing).

What still holds: Gemini's "apologetic" sentence softens naturally, its "excited" one lifts. No tags needed. That prosodic shaping from plain text is the thing other providers mostly need tags or SSML for.

𝐕𝐨𝐢𝐜𝐞 𝐪𝐮𝐚𝐥𝐢𝐭𝐲 𝐜𝐨𝐦𝐩𝐚𝐫𝐢𝐬𝐨𝐧:
(Matched character, warm/conversational female: Aoede, Alexandra, Katie — the agent voice each provider recommends.)

|                                | Gemini (Aoede) | ElevenLabs (Alexandra) | Cartesia (Katie) |
|--------------------------------|----------------|------------------------|------------------|
| Avg duration (same text)       | **4.29s**      | 2.92s                  | 2.99s            |
| Pause ratio                    | 28.9%          | 24.1%                  | 28.2%            |
| Pause range across sentences   | 21–35%         | 18–32%                 | 22–40%           |
| Energy variation (CV)          | 0.597          | **0.762**              | 0.614            |

𝐅𝐞𝐚𝐭𝐮𝐫𝐞 𝐜𝐨𝐦𝐩𝐚𝐫𝐢𝐬𝐨𝐧 (from vendor docs):

|                          | Gemini Flash TTS      | ElevenLabs Flash v2.5                                | Cartesia Sonic 3                      |
|--------------------------|-----------------------|------------------------------------------------------|---------------------------------------|
| Voices                   | 30 prebuilt           | Large library + cloning                              | Library + cloning                     |
| Languages                | 90+, auto-detect      | 32                                                   | 40+ (9 Indian)                        |
| Inline audio tags        | Open set              | [laughs], [whispers], [sighs], [door slam]           | [laughter] + pitch/speed/emotion      |
| Voice cloning            | No                    | Yes                                                  | Yes                                   |
| Streaming                | Vertex AI (preview)   | Native                                               | Native                                |
| Vendor TTFA claim        | —                     | ~75 ms                                               | ~90 ms                                |
| Our measured TTFA        | **696 ms p50**        | not retested                                         | not retested                          |

Then we added audio tags.

Write [whispers] inline and Gemini's voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio. [laughs] is a real laugh, not the word. [sighs] is a real exhale. SSML never got this right.

𝐖𝐡𝐚𝐭 𝐰𝐞 𝐦𝐞𝐚𝐬𝐮𝐫𝐞𝐝 (30 runs):

• First-chunk latency p50: 𝟔𝟗𝟔 𝐦𝐬 (p90 789 ms, p99 1,122 ms)
• Intelligibility round-trip: 𝟐.𝟗% 𝐖𝐄𝐑, 5 of 6 tag samples at 0.000
• Real-time factor: 𝟏.𝟔× (streams faster than playback)
• Naturalness: Elo 𝟏,𝟐𝟏𝟏 on Artificial Analysis (Google's claim; we did not run our own)

𝐖𝐡𝐚𝐭 𝐛𝐢𝐭 𝐮𝐬:

Latency. 696 ms p50. Fine for scripted and outbound; slower than you want for real-time turn-taking.

Multi-speaker. Tested three voice pairs (Puck+Kore, Fenrir+Leda, Charon+Leda). All three sounded like the same voice slightly modulating.

Dashboard with audio samples, charts, and side-by-side comparisons: https://dashboard-gemini-tts.vercel.app
Prior work: https://github.com/renuyadav972/gemini-s2s
