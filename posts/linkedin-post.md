# LinkedIn Post. Gemini Flash TTS, tested

Google shipped Gemini Flash TTS this week — their first dedicated TTS, first-party, runs on the same Vertex AI infrastructure as the rest of the model family. We wired it into a cascaded voice agent over Plivo telephony, ran real phone calls plus 30-run benchmarks, and here's what we learned about using it well.

𝐎𝐧𝐞 𝐠𝐨𝐭𝐜𝐡𝐚 𝐮𝐩 𝐟𝐫𝐨𝐧𝐭:

The 3.1 preview model needs Vertex AI API enabled, not just Cloud TTS. Without Vertex AI, the model doesn't stream — you get the whole utterance at once. The older 2.5 Flash TTS runs on vanilla Cloud TTS, but the new 3.1 preview routes through Vertex AI for streaming synthesis. Check this before you wire it up; it's not in the quickstart.

𝐖𝐡𝐲 𝐢𝐭'𝐬 𝐝𝐢𝐟𝐟𝐞𝐫𝐞𝐧𝐭:

Gemini TTS isn't a phoneme engine. It's an LLM that produces audio. It reads your whole prompt as context — voice descriptors, scene, emotional cues, and the actual line. Compared to traditional TTS where you pass text and a voice ID and that's the contract, this gives you more control and more rope.

𝐖𝐡𝐚𝐭 𝐲𝐨𝐮 𝐠𝐞𝐭 𝐢𝐧 𝐯𝟏:

• 30 prebuilt voices with tonal descriptors (Aoede, Puck, Charon, Kore — tagged "Bright," "Upbeat," "Informative," "Breathy")
• 90+ languages with auto-detection — the model picks up input language without you specifying it
• Inline audio tags as an open set. [whispers], [laughs], [sighs], [excited], [apologetic] all work, and tags you invent often work too
• Multi-speaker mode (up to 2 speakers in a single call)
• Director-style prompting: Audio Profile + Scene + Director's Notes for fine-grained voice direction
• 32k token context — feed it whole scenes, not just lines

𝐇𝐨𝐰 𝐰𝐞 𝐠𝐨𝐭 𝐭𝐡𝐞 𝐛𝐞𝐬𝐭 𝐨𝐮𝐭 𝐨𝐟 𝐢𝐭:

𝟏. 𝐏𝐥𝐚𝐢𝐧 𝐭𝐞𝐱𝐭 𝐚𝐥𝐫𝐞𝐚𝐝𝐲 𝐬𝐡𝐚𝐩𝐞𝐬 𝐩𝐫𝐨𝐬𝐨𝐝𝐲. With Aoede on six conversational sentences — no tags, no SSML — the "apologetic" line softens naturally. The "excited" one lifts. The model reads emotional intent from the words. For most lines, the simplest possible call gets you most of the way.

𝟐. 𝐈𝐧𝐥𝐢𝐧𝐞 𝐭𝐚𝐠𝐬 𝐬𝐮𝐫𝐯𝐢𝐯𝐞 𝐩𝐡𝐨𝐧𝐞 𝐜𝐨𝐝𝐞𝐜. Write [whispers] inline and the voice actually whispers — mid-sentence, over 8 kHz μ-law. [laughs] is a real laugh, not the word. [sighs] is a real exhale. We measured 5 of 6 tagged samples at 0.000 WER round-trip — words intact even through phone compression.

𝟑. 𝐒𝐭𝐫𝐞𝐚𝐦, 𝐝𝐨𝐧'𝐭 𝐰𝐚𝐢𝐭. Real-time factor is 1.6× — the model produces audio faster than playback consumes it. Start playing on the first chunk and the listener hears 696 ms of pre-roll, not the full utterance.

𝟒. 𝐌𝐮𝐥𝐭𝐢-𝐬𝐩𝐞𝐚𝐤𝐞𝐫 𝐢𝐬 𝐰𝐞𝐚𝐤 𝐭𝐨𝐝𝐚𝐲. We tested three voice pairs (Puck+Kore, Fenrir+Leda, Charon+Leda). All three sounded like the same voice slightly modulating. If you need real two-character dialog, run two separate calls with different voices.

𝐏𝐫𝐨𝐝𝐮𝐜𝐭𝐢𝐨𝐧 𝐧𝐮𝐦𝐛𝐞𝐫𝐬 (30 runs):

• First-chunk latency p50: 𝟔𝟗𝟔 𝐦𝐬 (p90 789, p99 1,122)
• Real-time factor: 𝟏.𝟔× (streams faster than playback)
• Intelligibility round-trip WER: 𝟐.𝟗% overall, 5 of 6 tag samples at 0.000

𝐖𝐡𝐞𝐫𝐞 𝐢𝐭 𝐟𝐢𝐭𝐬 𝐭𝐨𝐝𝐚𝐲:

696 ms p50 is fine for scripted, IVR, outbound, and one-shot synthesis. Sub-300ms real-time turn-taking is slower than you want — the expressiveness tradeoff is real. For voice agents where each turn is generated and then played — scripted prompts, outbound calling, conversational personas — Gemini sounds noticeably more human than what's been available before. Pick your spots.

Dashboard with audio samples: https://dashboard-gemini-tts.vercel.app
Repo: https://github.com/renuyadav972/gemini-tts
