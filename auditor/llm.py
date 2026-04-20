from __future__ import annotations

import json
import os
from typing import Optional

from .fetch import FetchResult
from .heuristics import HeuristicReport

SYSTEM = (
    "You are a senior web growth auditor working for Levvate, a high-conversion "
    "website agency. You review one site at a time and write findings that a sales "
    "rep can read aloud on a discovery call. Be specific, blunt, and tie every "
    "observation to revenue (lead capture, trust, conversion). No fluff. No hedging."
)

SCHEMA_HINT = """
Return ONLY a JSON object with this exact shape:

{
  "executive_summary": "<2-4 sentence top-line for the prospect>",
  "biggest_opportunity": "<one sentence: the single change that would move conversions most>",
  "findings": [
    {
      "category": "<SEO|Accessibility|Performance|Conversion|Brand>",
      "title": "<short title>",
      "severity": "<low|medium|high>",
      "observation": "<what is happening on the site>",
      "recommendation": "<concrete next action a developer can take>"
    }
  ],
  "next_steps": ["<step 1>", "<step 2>", "<step 3>"]
}

Aim for 5 to 7 findings. Do not invent metrics you cannot see in the inputs.
"""


def enrich_with_llm(
    fetch_result: FetchResult,
    heur: HeuristicReport,
) -> Optional[dict]:
    """Call Claude to produce a sales-ready narrative. Returns None if unavailable."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    try:
        import anthropic  # noqa
    except ImportError:
        return None

    client = anthropic.Anthropic()

    soup = fetch_result.soup
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")][:3]
    h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:6]
    body_snippet = soup.get_text(" ", strip=True)[:2500]

    heuristics_dump = "\n".join(
        f"- [{c.status.upper():4}] {c.category} / {c.name}: {c.detail}"
        for c in heur.checks
    )

    user_prompt = f"""Site: {fetch_result.final_url}
Status: {fetch_result.status_code} | Bytes: {fetch_result.content_bytes} | TTFB: {fetch_result.elapsed_ms} ms

Title: {title}
H1s: {h1s}
H2s: {h2s}

Heuristic check results:
{heuristics_dump}

Body text excerpt:
\"\"\"
{body_snippet}
\"\"\"

{SCHEMA_HINT}
"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip("` \n")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}
