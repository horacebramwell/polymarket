from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.request import Request, urlopen

DOCS_INDEX_URL = "https://docs.polymarket.us/llms.txt"
REQUIRED_DOC_SUFFIXES = (
    "/api-reference/authentication.md",
    "/api-reference/rate-limits.md",
    "/api-reference/orders/create-order.md",
    "/api-reference/orders/preview-order.md",
    "/api-reference/orders/modify-order.md",
    "/api-reference/orders/cancel-order.md",
    "/api-reference/orders/cancel-all-open-orders.md",
    "/api-reference/orders/close-position-order.md",
    "/api-reference/events/get-events.md",
    "/api-reference/markets/get-market-bbo.md",
    "/api-reference/markets/get-market-book.md",
    "/api-reference/portfolio/get-user-positions.md",
    "/api-reference/account/get-account-balances.md",
    "/api-reference/search/search.md",
    "/api-reference/sdks/python/quickstart.md",
    "/api-reference/sdks/python/orders.md",
    "/api-reference/websocket/overview.md",
)

_ENTRY_RE = re.compile(r"^- \[(?P<title>[^]]+)\]\((?P<url>https://docs\.polymarket\.us/[^)]+)\)(?:: (?P<description>.*))?$")


@dataclass(frozen=True)
class DocEntry:
    title: str
    url: str
    description: str = ""


def parse_docs_index(text: str) -> list[DocEntry]:
    entries: list[DocEntry] = []
    for line in text.splitlines():
        match = _ENTRY_RE.match(line.strip())
        if match:
            entries.append(
                DocEntry(
                    title=match.group("title"),
                    url=match.group("url"),
                    description=match.group("description") or "",
                )
            )
    return entries


def fetch_docs_index(url: str = DOCS_INDEX_URL, timeout: float = 10.0) -> str:
    request = Request(url, headers={"User-Agent": "polymarket-us-agent-skill/0.1"})
    with urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def check_required_docs(fetcher=fetch_docs_index) -> dict[str, object]:
    text = fetcher(DOCS_INDEX_URL)
    entries = parse_docs_index(text)
    urls = {entry.url for entry in entries}
    matched: list[str] = []
    missing: list[str] = []
    for suffix in REQUIRED_DOC_SUFFIXES:
        if any(url.endswith(suffix) for url in urls):
            matched.append(suffix)
        else:
            missing.append(suffix)
    return {
        "ok": not missing,
        "source": DOCS_INDEX_URL,
        "entryCount": len(entries),
        "matched": matched,
        "missing": missing,
    }
