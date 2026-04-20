from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (compatible; AISiteAuditor/0.1; "
    "+https://github.com/yusufdxb/ai-site-auditor)"
)


@dataclass
class FetchResult:
    url: str
    final_url: str
    status_code: int
    elapsed_ms: int
    content_bytes: int
    html: str
    soup: BeautifulSoup
    headers: dict


def fetch(url: str, timeout: int = 15) -> FetchResult:
    if not urlparse(url).scheme:
        url = "https://" + url

    t0 = time.perf_counter()
    resp = requests.get(
        url,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
        allow_redirects=True,
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    return FetchResult(
        url=url,
        final_url=resp.url,
        status_code=resp.status_code,
        elapsed_ms=elapsed_ms,
        content_bytes=len(resp.content),
        html=html,
        soup=soup,
        headers=dict(resp.headers),
    )
