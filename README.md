# AI Site Auditor

URL in, structured PDF site audit out. Single command. Built as a working prototype
of the AI Site Assessment Generator described in Levvate's
*AI Automation & Web Development Intern* job spec.

## What it does

```
python audit.py https://example.com
```

Pipeline:

1. **Fetch** the URL, capture status, latency, payload size, headers, and parsed DOM.
2. **Heuristics** -- deterministic checks for SEO (title, meta, H1, canonical, OG tags),
   accessibility (alt-text coverage, viewport, html `lang`), performance (HTML size,
   TTFB proxy, script count), and conversion (HTTPS, CTA verbs, lead capture forms).
   Aggregated into a 0-100 score with pass/warn/fail counts.
3. **LLM enrichment** -- Claude is given the heuristic results plus a content excerpt
   and asked to produce a sales-ready narrative against a fixed JSON schema:
   executive summary, biggest opportunity, 5-7 categorized findings with
   severity + recommendation, and a 3-step next-actions list. Schema is enforced
   so the PDF template can rely on the structure.
4. **Render** a branded PDF via Jinja2 + WeasyPrint. Server-side, deterministic,
   no manual editing required.

End-to-end run: typically under 15 seconds per site.

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

The script runs without a key (heuristic-only mode); it just skips the strategic
findings section in the PDF.

## Why this design

**Deterministic + generative.** Heuristics give the audit a verifiable backbone --
every claim in the "Technical Checks" section maps to a measurable signal. The LLM
layer adds the framing and recommendations a sales rep needs on a discovery call,
without being trusted to invent metrics it can't see.

**Schema-enforced output.** The Claude call returns JSON, not prose. That makes the
template stable, and lets us swap the model or tighten the prompt without breaking
the renderer.

**Eval-ready.** A small set of hand-audited sites under `examples/` would let us
iterate the prompt against ground truth and gate model bumps on regression.

## File layout

```
ai-site-auditor/
├── audit.py                  CLI entrypoint
├── requirements.txt
├── auditor/
│   ├── fetch.py              HTTP + parse
│   ├── heuristics.py         Deterministic checks + scoring
│   ├── llm.py                Anthropic call + JSON schema
│   └── render.py             Jinja2 + WeasyPrint
└── templates/
    └── report.html           Branded PDF template
```

## Status

Prototype, ~400 LOC. Built in one session as the bonus deliverable for the
Levvate application. Author: Yusuf Guenena (yusuf.a.guenena@gmail.com).
