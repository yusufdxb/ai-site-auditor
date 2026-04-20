from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse

from .fetch import FetchResult


@dataclass
class Check:
    category: str
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: str


@dataclass
class HeuristicReport:
    checks: List[Check] = field(default_factory=list)
    summary: dict = field(default_factory=dict)


def run_heuristics(fetch_result: FetchResult) -> HeuristicReport:
    soup = fetch_result.soup
    report = HeuristicReport()
    add = report.checks.append

    # --- SEO ---
    title = (soup.title.string.strip() if soup.title and soup.title.string else "")
    if not title:
        add(Check("SEO", "Page title", "fail", "Missing <title> tag."))
    elif len(title) < 20 or len(title) > 65:
        add(Check("SEO", "Page title", "warn",
                  f"Title is {len(title)} chars; aim for 30-60."))
    else:
        add(Check("SEO", "Page title", "pass", f"\"{title}\" ({len(title)} chars)."))

    desc = soup.find("meta", attrs={"name": "description"})
    desc_content = (desc.get("content") or "").strip() if desc else ""
    if not desc_content:
        add(Check("SEO", "Meta description", "fail",
                  "No meta description; search engines auto-generate one."))
    elif len(desc_content) < 70 or len(desc_content) > 165:
        add(Check("SEO", "Meta description", "warn",
                  f"Description is {len(desc_content)} chars; aim for 120-155."))
    else:
        add(Check("SEO", "Meta description", "pass",
                  f"{len(desc_content)} chars, in target range."))

    h1s = soup.find_all("h1")
    if len(h1s) == 0:
        add(Check("SEO", "H1 heading", "fail", "No H1 on the page."))
    elif len(h1s) > 1:
        add(Check("SEO", "H1 heading", "warn",
                  f"{len(h1s)} H1 tags found; use exactly one."))
    else:
        add(Check("SEO", "H1 heading", "pass",
                  f"One H1: \"{h1s[0].get_text(strip=True)[:80]}\""))

    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        add(Check("SEO", "Canonical URL", "pass", canonical.get("href")))
    else:
        add(Check("SEO", "Canonical URL", "warn",
                  "No canonical link; can cause duplicate-content issues."))

    og_tags = soup.find_all("meta", attrs={"property": lambda v: v and v.startswith("og:")})
    if len(og_tags) >= 4:
        add(Check("SEO", "OpenGraph tags", "pass",
                  f"{len(og_tags)} og: tags present (good for social previews)."))
    else:
        add(Check("SEO", "OpenGraph tags", "warn",
                  f"Only {len(og_tags)} og: tags; add og:title, og:description, og:image, og:url."))

    # --- Accessibility ---
    imgs = soup.find_all("img")
    if imgs:
        without_alt = [i for i in imgs if not (i.get("alt") or "").strip()]
        coverage = 100 * (len(imgs) - len(without_alt)) // len(imgs)
        if without_alt:
            add(Check("Accessibility", "Image alt text", "warn" if coverage >= 70 else "fail",
                      f"{len(without_alt)} of {len(imgs)} images missing alt ({coverage}% coverage)."))
        else:
            add(Check("Accessibility", "Image alt text", "pass",
                      f"All {len(imgs)} images have alt text."))

    if not soup.find("html").get("lang"):
        add(Check("Accessibility", "HTML lang attribute", "fail",
                  "<html> tag has no lang attribute; screen readers can't pick correct voice."))
    else:
        add(Check("Accessibility", "HTML lang attribute", "pass",
                  f"lang=\"{soup.find('html').get('lang')}\""))

    viewport = soup.find("meta", attrs={"name": "viewport"})
    if viewport and "width" in (viewport.get("content") or ""):
        add(Check("Accessibility", "Mobile viewport", "pass", viewport.get("content")))
    else:
        add(Check("Accessibility", "Mobile viewport", "fail",
                  "No viewport meta; site won't render correctly on mobile."))

    # --- Performance ---
    size_kb = fetch_result.content_bytes / 1024
    if size_kb > 1500:
        add(Check("Performance", "HTML payload size", "fail",
                  f"{size_kb:.0f} KB is large; target under 500 KB."))
    elif size_kb > 500:
        add(Check("Performance", "HTML payload size", "warn",
                  f"{size_kb:.0f} KB; consider trimming inlined assets."))
    else:
        add(Check("Performance", "HTML payload size", "pass", f"{size_kb:.0f} KB."))

    if fetch_result.elapsed_ms > 3000:
        add(Check("Performance", "Time to first byte (proxy)", "fail",
                  f"{fetch_result.elapsed_ms} ms server response."))
    elif fetch_result.elapsed_ms > 1500:
        add(Check("Performance", "Time to first byte (proxy)", "warn",
                  f"{fetch_result.elapsed_ms} ms server response."))
    else:
        add(Check("Performance", "Time to first byte (proxy)", "pass",
                  f"{fetch_result.elapsed_ms} ms server response."))

    scripts = soup.find_all("script", src=True)
    if len(scripts) > 30:
        add(Check("Performance", "External scripts", "warn",
                  f"{len(scripts)} external <script> tags can block rendering."))
    else:
        add(Check("Performance", "External scripts", "pass",
                  f"{len(scripts)} external scripts."))

    # --- Conversion / Trust ---
    if urlparse(fetch_result.final_url).scheme != "https":
        add(Check("Conversion", "HTTPS", "fail", "Site is not served over HTTPS."))
    else:
        add(Check("Conversion", "HTTPS", "pass", "Served over HTTPS."))

    # CTAs: heuristic, links/buttons with action verbs
    text = soup.get_text(" ", strip=True).lower()
    cta_words = ["book", "schedule", "get started", "start free", "contact", "request",
                 "demo", "buy", "subscribe", "sign up", "get a quote"]
    found_ctas = [w for w in cta_words if w in text]
    if len(found_ctas) >= 2:
        add(Check("Conversion", "Call-to-action language", "pass",
                  f"Found CTA verbs: {', '.join(found_ctas[:5])}."))
    else:
        add(Check("Conversion", "Call-to-action language", "warn",
                  "Few obvious CTAs detected; visitors may not know the next step."))

    forms = soup.find_all("form")
    if forms:
        add(Check("Conversion", "Lead capture form", "pass",
                  f"{len(forms)} form(s) on the page."))
    else:
        add(Check("Conversion", "Lead capture form", "warn",
                  "No <form> on the homepage; add a low-friction lead capture."))

    # --- Summary ---
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for c in report.checks:
        counts[c.status] += 1
    score = max(0, 100 - (counts["warn"] * 5) - (counts["fail"] * 12))
    report.summary = {
        "score": score,
        "pass": counts["pass"],
        "warn": counts["warn"],
        "fail": counts["fail"],
        "total": len(report.checks),
    }
    return report
