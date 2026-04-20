#!/usr/bin/env python3
"""AI Site Auditor -- URL in, structured PDF site audit out.

Usage:
    python audit.py https://example.com
    python audit.py example.com --out my_audit.pdf
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from auditor.fetch import fetch
from auditor.heuristics import run_heuristics
from auditor.llm import enrich_with_llm
from auditor.render import render_pdf


def slugify(url: str) -> str:
    host = urlparse(url).netloc or url
    return host.replace(".", "_").replace(":", "_")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate a site audit PDF.")
    ap.add_argument("url", help="Site URL (with or without scheme).")
    ap.add_argument("--out", help="Output PDF path. Defaults to audit_<host>_<ts>.pdf")
    ap.add_argument("--no-llm", action="store_true",
                    help="Skip the Claude enrichment step (heuristics only).")
    args = ap.parse_args()

    t0 = time.perf_counter()
    print(f"[1/4] Fetching {args.url} ...", flush=True)
    fr = fetch(args.url)
    print(f"      HTTP {fr.status_code} | {fr.content_bytes/1024:.0f} KB | {fr.elapsed_ms} ms", flush=True)

    print("[2/4] Running deterministic heuristics ...", flush=True)
    heur = run_heuristics(fr)
    print(f"      score={heur.summary['score']} pass={heur.summary['pass']} "
          f"warn={heur.summary['warn']} fail={heur.summary['fail']}", flush=True)

    llm = None
    if args.no_llm:
        print("[3/4] LLM enrichment skipped (--no-llm).", flush=True)
    else:
        print("[3/4] Asking Claude for strategic findings ...", flush=True)
        llm = enrich_with_llm(fr, heur)
        if llm is None:
            print("      Skipped: ANTHROPIC_API_KEY not set or anthropic SDK missing.",
                  flush=True)
        else:
            print(f"      {len(llm.get('findings', []))} findings returned.", flush=True)

    out = args.out or f"audit_{slugify(fr.final_url)}_{datetime.utcnow():%Y%m%d_%H%M%S}.pdf"
    print(f"[4/4] Rendering PDF to {out} ...", flush=True)
    render_pdf(fr, heur, llm, out)
    print(f"      Done in {time.perf_counter() - t0:.1f}s.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
