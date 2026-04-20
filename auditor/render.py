from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from .fetch import FetchResult
from .heuristics import HeuristicReport

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def render_pdf(
    fetch_result: FetchResult,
    heur: HeuristicReport,
    llm_findings: dict | None,
    out_path: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("report.html")
    html_str = template.render(
        site_url=fetch_result.final_url,
        generated_at=datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC"),
        heur=heur,
        llm=llm_findings,
        status=fetch_result.status_code,
        ttfb_ms=fetch_result.elapsed_ms,
        size_kb=fetch_result.content_bytes / 1024,
    )
    HTML(string=html_str).write_pdf(out_path)
    return out_path
