// Generate .docx + .html versions of the LinkedIn and X posts.
// Usage: node posts/make_docs.js

const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun,
  HeadingLevel, AlignmentType, LevelFormat,
  ExternalHyperlink, BorderStyle,
  Table, TableRow, TableCell, WidthType, ShadingType,
} = require('docx');

// -----------------------------------------------------------------------------
// DOCX defaults
// -----------------------------------------------------------------------------

const pageSetup = {
  size: { width: 12240, height: 15840 },
  margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 },
};

const defaultStyles = {
  default: { document: { run: { font: 'Arial', size: 22 } } },
  paragraphStyles: [
    {
      id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 32, bold: true, font: 'Arial' },
      paragraph: { spacing: { before: 0, after: 240 }, outlineLevel: 0 },
    },
    {
      id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
      run: { size: 26, bold: true, font: 'Arial' },
      paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 },
    },
  ],
};

const numbering = { config: [] };

// -----------------------------------------------------------------------------
// Helpers
// -----------------------------------------------------------------------------

const p = (text, opts = {}) => new Paragraph({
  spacing: { before: 0, after: 160 },
  children: [new TextRun({ text, ...opts })],
});

const bold = (text) => new Paragraph({
  spacing: { before: 120, after: 80 },
  children: [new TextRun({ text, bold: true })],
});

const quote = (text) => new Paragraph({
  spacing: { before: 100, after: 180 },
  indent: { left: 720 },
  border: { left: { style: BorderStyle.SINGLE, size: 8, color: 'CCCCCC', space: 8 } },
  children: [new TextRun({ text, italics: true })],
});

// Table builders
const border = { style: BorderStyle.SINGLE, size: 4, color: 'CCCCCC' };
const borders = { top: border, bottom: border, left: border, right: border };

const cell = (text, opts = {}) => new TableCell({
  borders,
  width: { size: opts.width || 4680, type: WidthType.DXA },
  shading: opts.header ? { fill: 'F3F3F1', type: ShadingType.CLEAR } : undefined,
  margins: { top: 80, bottom: 80, left: 120, right: 120 },
  children: [new Paragraph({
    children: Array.isArray(text)
      ? text
      : [new TextRun({ text, bold: !!opts.header, italics: !!opts.italic })],
  })],
});

const headerRow = (labels, widths) => new TableRow({
  tableHeader: true,
  children: labels.map((label, i) => cell(label, { width: widths[i], header: true })),
});

const bodyRow = (values, widths) => new TableRow({
  children: values.map((v, i) => cell(v, { width: widths[i] })),
});

const table = (header, rows, widths) => new Table({
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  columnWidths: widths,
  rows: [headerRow(header, widths), ...rows.map(r => bodyRow(r, widths))],
});

// -----------------------------------------------------------------------------
// LinkedIn
// -----------------------------------------------------------------------------

const TAG_WIDTHS = [2200, 7160];
const CAVEAT_WIDTHS = [2200, 7160];
const COMPARE_WIDTHS = [3400, 2800, 3160];

const METRIC_WIDTHS = [3900, 5460];

const linkedinChildren = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('Gemini Flash TTS, tested')] }),

  p('Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.'),

  quote('[sighs] Yes, I can help with that. 237 times 18 is 4266.'),
  p('The sigh is a real exhale. Math is right. Phone codec didn\'t flatten it.'),

  new Paragraph({ spacing: { before: 220, after: 80 }, children: [new TextRun({ text: 'What we measured:', bold: true })] }),
  table(
    ['Metric', 'Result'],
    [
      ['First-chunk latency p50 (30 runs)', '696 ms   (p90 789 ms, p99 1,122 ms)'],
      ['Intelligibility round-trip (WER)',  '2.9% overall, 5 of 6 tag samples at 0.000'],
      ['Real-time factor',                    '1.6×   (streams faster than playback)'],
      ['Naturalness (Google\'s claim)',       'Elo 1,211 on Artificial Analysis (blind human preference; we did not run our own)'],
    ],
    METRIC_WIDTHS
  ),

  new Paragraph({ spacing: { before: 240, after: 80 }, children: [new TextRun({ text: 'What stood out:', bold: true })] }),

  new Paragraph({
    spacing: { before: 0, after: 140 },
    children: [
      new TextRun({ text: 'Shifts are mid-sentence, not per-line. ', bold: true }),
      new TextRun('The voice drops to a whisper and comes back up inside the same utterance. SSML never got this right.'),
    ],
  }),

  new Paragraph({
    spacing: { before: 0, after: 140 },
    children: [
      new TextRun({ text: '[laughs] is a real laugh, not the word. ', bold: true }),
      new TextRun('Same for [sighs]. The model generates the non-verbal sound inline, no pre-recorded splices.'),
    ],
  }),

  new Paragraph({
    spacing: { before: 0, after: 180 },
    children: [
      new TextRun({ text: 'The 8 kHz codec usually destroys prosody nuance. ', bold: true }),
      new TextRun('Here it didn\'t. That matters because phone audio is where most voice agents actually live.'),
    ],
  }),

  new Paragraph({ spacing: { before: 220, after: 80 }, children: [new TextRun({ text: 'What bit us:', bold: true })] }),
  table(
    ['Area', 'Finding'],
    [
      ['Latency',       '696 ms p50 is 3 to 10 times slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms). Fine for scripted, too slow for real-time turns.'],
      ['Auth',          'The 3.1 preview needs Vertex AI API enabled, not just Cloud TTS. The 2.5 version runs on vanilla Cloud TTS.'],
      ['Multi-speaker', 'Tested Puck+Kore, Fenrir+Leda, Charon+Leda. All three pairs sounded like the same voice slightly modulating.'],
    ],
    CAVEAT_WIDTHS
  ),

  new Paragraph({
    spacing: { before: 260, after: 160 },
    children: [
      new TextRun('Google\'s release cadence is the tell. Flash Live three weeks ago. Flash TTS this week. Both first-party. Google knows neither wins alone. They\'re shipping both so builders route per turn, not per philosophy.'),
    ],
  }),

  new Paragraph({
    spacing: { before: 180, after: 40 },
    children: [new TextRun({ text: 'Dashboard with charts, audio samples, and raw data: [dashboard URL]', italics: true })],
  }),
  new Paragraph({
    spacing: { before: 0, after: 0 },
    children: [
      new TextRun('Prior work: '),
      new ExternalHyperlink({
        children: [new TextRun({ text: 'https://github.com/renuyadav972/gemini-s2s', style: 'Hyperlink' })],
        link: 'https://github.com/renuyadav972/gemini-s2s',
      }),
    ],
  }),
];

const linkedinDoc = new Document({
  styles: defaultStyles, numbering,
  sections: [{ properties: { page: pageSetup }, children: linkedinChildren }],
});

// -----------------------------------------------------------------------------
// X post
// -----------------------------------------------------------------------------

const optionHeader = (txt) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(txt)] });
const tweetNum = (n) => new Paragraph({
  spacing: { before: 160, after: 40 },
  children: [new TextRun({ text: `${n}/`, bold: true })],
});

const xChildren = [
  new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun('Gemini Flash TTS, tested. X drafts')] }),

  optionHeader('Option A. Single tweet'),
  p('Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.'),
  p('First-chunk p50 696 ms though. 3 to 10x slower than ElevenLabs Flash or Cartesia for live turns.'),

  optionHeader('Option B. Thread (6 tweets)'),

  tweetNum(1),
  p('Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.'),
  p('Wired it into a cascaded agent (Cloud STT + Gemini LLM + Flash TTS) over Plivo, plus 30 back-to-back runs of our own.'),

  tweetNum(2),
  p('One turn. Caller asked for 237 × 18. LLM wrote:'),
  quote('[sighs] Yes, I can help with that. 237 times 18 is 4266.'),
  p('Sigh is a real exhale. Math is right. Phone codec didn\'t flatten it.'),

  tweetNum(3),
  p('What we measured (30 runs + WER round-trip):'),
  p('• First-chunk p50: 696 ms (p90 789, p99 1,122)'),
  p('• WER round-trip: 2.9% overall, 5 of 6 samples at 0.000'),
  p('• Duration CV: 0.029 (pacing near-identical run to run)'),
  p('• Real-time factor: 1.6×'),

  tweetNum(4),
  p('What stood out:'),
  p('Shifts are mid-sentence, not per-line. Voice drops to whisper, comes back up inside the same utterance.'),
  p('[laughs] is a real laugh, not the word. Non-verbal sounds generated inline, no splices.'),
  p('8 kHz phone codec didn\'t destroy it. That matters.'),

  tweetNum(5),
  p('What bit us:'),
  p('Latency 696 ms p50. Slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms).'),
  p('3.1 preview needs Vertex AI, not just Cloud TTS.'),
  p('Multi-speaker: 3 voice pairs, all sounded like the same voice modulating.'),

  tweetNum(6),
  p('Google\'s cadence is the tell. Flash Live three weeks ago. Flash TTS this week. Both first-party.'),
  p('Google knows neither wins alone. They\'re shipping both so builders route per turn, not per philosophy.'),
  new Paragraph({
    spacing: { before: 100, after: 0 },
    children: [new TextRun({ text: 'Dashboard: [URL]', italics: true })],
  }),
  new Paragraph({
    spacing: { before: 0, after: 120 },
    children: [
      new TextRun('Prior: '),
      new ExternalHyperlink({
        children: [new TextRun({ text: 'https://github.com/renuyadav972/gemini-s2s', style: 'Hyperlink' })],
        link: 'https://github.com/renuyadav972/gemini-s2s',
      }),
    ],
  }),

  optionHeader('Option C. Short single observation'),
  p('Gemini 3.1 Flash TTS. Write [whispers] inline, voice actually whispers. Mid-sentence. Over phone audio.'),
  p('Measured WER round-trip 2.9%, 5 of 6 tag samples letter-perfect. Latency p50 696 ms though. 3 to 10x slower than ElevenLabs Flash.'),
];

const xDoc = new Document({
  styles: defaultStyles, numbering,
  sections: [{ properties: { page: pageSetup }, children: xChildren }],
});

// -----------------------------------------------------------------------------
// HTML versions
// -----------------------------------------------------------------------------

const htmlShell = (title, body) => `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>${title}</title>
<style>
  @media print { body { font-size: 11pt; } .divider { page-break-inside: avoid; } }
  body {
    font: 15px/1.65 -apple-system, BlinkMacSystemFont, "SF Pro Text", Arial, sans-serif;
    max-width: 720px; margin: 48px auto; padding: 0 24px; color: #111; background: #fafaf8;
  }
  h1 { font-size: 24px; letter-spacing: -0.01em; margin: 0 0 8px; }
  h2 { font-size: 17px; margin: 28px 0 6px; letter-spacing: -0.005em; }
  p  { margin: 0 0 14px; }
  .lead { font-weight: 700; margin: 20px 0 8px; }
  blockquote {
    margin: 14px 0 18px; padding: 6px 16px; border-left: 3px solid #d0d0cc;
    color: #333; font-style: italic;
  }
  table { border-collapse: collapse; width: 100%; margin: 10px 0 20px; font-size: 14px; }
  th, td { border: 1px solid #d6d6d1; padding: 8px 12px; text-align: left; vertical-align: top; }
  th { background: #f3f3f1; font-weight: 700; font-size: 13px; letter-spacing: 0.01em; text-transform: uppercase; color: #333; }
  td:first-child { white-space: nowrap; font-weight: 600; }
  .tweet-num { font-weight: 700; margin: 16px 0 4px; }
  a { color: #0b5cad; text-decoration: none; } a:hover { text-decoration: underline; }
  .pullquote { font-weight: 700; font-size: 16px; margin: 22px 0 12px; line-height: 1.45; }
</style>
</head>
<body>
${body}
</body>
</html>`;

const linkedinHtml = htmlShell('Gemini Flash TTS, tested', `
<h1>Gemini Flash TTS, tested</h1>

<p>Write <code>[whispers]</code> inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.</p>

<blockquote>[sighs] Yes, I can help with that. 237 times 18 is 4266.</blockquote>
<p>The sigh is a real exhale. Math is right. Phone codec didn't flatten it.</p>

<p class="lead">What we measured:</p>
<table>
  <thead><tr><th>Metric</th><th>Result</th></tr></thead>
  <tbody>
    <tr><td>First-chunk latency p50 (30 runs)</td><td><b>696 ms</b> (p90 789 ms, p99 1,122 ms)</td></tr>
    <tr><td>Intelligibility round-trip (WER)</td><td><b>2.9% overall</b>, 5 of 6 tag samples at 0.000</td></tr>
    <tr><td>Real-time factor</td><td>1.6× (streams faster than playback)</td></tr>
    <tr><td>Naturalness (Google's claim)</td><td>Elo 1,211 on Artificial Analysis (blind human preference; we did not run our own)</td></tr>
  </tbody>
</table>

<p class="lead">What stood out:</p>

<p><b>Shifts are mid-sentence, not per-line.</b> The voice drops to a whisper and comes back up inside the same utterance. SSML never got this right.</p>

<p><b>[laughs] is a real laugh, not the word.</b> Same for [sighs]. The model generates the non-verbal sound inline, no pre-recorded splices.</p>

<p><b>The 8 kHz codec usually destroys prosody nuance.</b> Here it didn't. That matters because phone audio is where most voice agents actually live.</p>

<p class="lead">What bit us:</p>
<table>
  <thead><tr><th>Area</th><th>Finding</th></tr></thead>
  <tbody>
    <tr><td>Latency</td><td>696 ms p50 is 3 to 10 times slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms). Fine for scripted, too slow for real-time turns.</td></tr>
    <tr><td>Auth</td><td>The 3.1 preview needs Vertex AI API enabled, not just Cloud TTS. The 2.5 version runs on vanilla Cloud TTS.</td></tr>
    <tr><td>Multi-speaker</td><td>Tested Puck+Kore, Fenrir+Leda, Charon+Leda. All three pairs sounded like the same voice slightly modulating.</td></tr>
  </tbody>
</table>

<p>Google's release cadence is the tell. Flash Live three weeks ago. Flash TTS this week. Both first-party. Google knows neither wins alone. They're shipping both so builders route per turn, not per philosophy.</p>

<p style="margin-top: 22px;"><i>Dashboard with charts, audio samples, and raw data: [dashboard URL]</i></p>
<p>Prior work: <a href="https://github.com/renuyadav972/gemini-s2s">https://github.com/renuyadav972/gemini-s2s</a></p>
`);

const xHtml = htmlShell('X Post drafts. Gemini Flash TTS', `
<h1>Gemini Flash TTS, tested. X drafts</h1>

<h2>Option A. Single tweet</h2>
<p>Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.</p>
<p>First-chunk p50 696 ms though. 3 to 10x slower than ElevenLabs Flash or Cartesia for live turns.</p>

<h2>Option B. Thread (6 tweets)</h2>

<div class="tweet-num">1/</div>
<p>Write [whispers] inline in Gemini 3.1 Flash TTS and the voice actually whispers. Mid-sentence. Over 8 kHz μ-law phone audio.</p>
<p>Wired it into a cascaded agent (Cloud STT + Gemini LLM + Flash TTS) over Plivo, plus 30 back-to-back runs of our own.</p>

<div class="tweet-num">2/</div>
<p>One turn. Caller asked for 237 × 18. LLM wrote:</p>
<blockquote>[sighs] Yes, I can help with that. 237 times 18 is 4266.</blockquote>
<p>Sigh is a real exhale. Math is right. Phone codec didn't flatten it.</p>

<div class="tweet-num">3/</div>
<p>What we measured (30 runs + WER round-trip):</p>
<p>
  • First-chunk p50: 696 ms (p90 789, p99 1,122)<br/>
  • WER round-trip: 2.9% overall, 5 of 6 samples at 0.000<br/>
  • Duration CV: 0.029 (pacing near-identical run to run)<br/>
  • Real-time factor: 1.6×
</p>

<div class="tweet-num">4/</div>
<p>What stood out:</p>
<p>Shifts are mid-sentence, not per-line. Voice drops to whisper, comes back up inside the same utterance.</p>
<p>[laughs] is a real laugh, not the word. Non-verbal sounds generated inline, no splices.</p>
<p>8 kHz phone codec didn't destroy it. That matters.</p>

<div class="tweet-num">5/</div>
<p>What bit us:</p>
<p>Latency 696 ms p50. Slower than ElevenLabs Flash (75 to 150 ms) or Cartesia Sonic 3 (40 to 90 ms).<br/>
3.1 preview needs Vertex AI, not just Cloud TTS.<br/>
Multi-speaker: 3 voice pairs, all sounded like the same voice modulating.</p>

<div class="tweet-num">6/</div>
<p>Google's cadence is the tell. Flash Live three weeks ago. Flash TTS this week. Both first-party.</p>
<p>Google knows neither wins alone. They're shipping both so builders route per turn, not per philosophy.</p>
<p>Dashboard: [URL]<br/>
Prior: <a href="https://github.com/renuyadav972/gemini-s2s">https://github.com/renuyadav972/gemini-s2s</a></p>

<h2>Option C. Short single observation</h2>
<p>Gemini 3.1 Flash TTS. Write [whispers] inline, voice actually whispers. Mid-sentence. Over phone audio.</p>
<p>Measured WER round-trip 2.9%, 5 of 6 tag samples letter-perfect. Latency p50 696 ms though. 3 to 10x slower than ElevenLabs Flash.</p>
`);

// -----------------------------------------------------------------------------
// Write all four
// -----------------------------------------------------------------------------

(async () => {
  const outDir = path.dirname(__filename);
  fs.writeFileSync(path.join(outDir, 'linkedin-post.docx'), await Packer.toBuffer(linkedinDoc));
  fs.writeFileSync(path.join(outDir, 'linkedin-post.html'), linkedinHtml);
  fs.writeFileSync(path.join(outDir, 'x-post.docx'), await Packer.toBuffer(xDoc));
  fs.writeFileSync(path.join(outDir, 'x-post.html'), xHtml);
  console.log('Wrote: linkedin-post.docx, linkedin-post.html, x-post.docx, x-post.html');
})();
