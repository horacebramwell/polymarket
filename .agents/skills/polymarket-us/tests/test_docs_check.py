from __future__ import annotations

from pmus_core import docs_check


FIXTURE = """# Polymarket US Documentation
- [Authentication](https://docs.polymarket.us/api-reference/authentication.md): Auth
- [Create Order](https://docs.polymarket.us/api-reference/orders/create-order.md): Create
- [Preview Order](https://docs.polymarket.us/api-reference/orders/preview-order.md): Preview
"""


def test_parse_docs_index_extracts_titles_urls_and_descriptions():
    entries = docs_check.parse_docs_index(FIXTURE)
    assert entries[0].title == "Authentication"
    assert entries[0].url.endswith("/api-reference/authentication.md")
    assert entries[0].description == "Auth"


def test_check_required_docs_reports_missing_entries():
    result = docs_check.check_required_docs(fetcher=lambda _url: FIXTURE)
    assert result["ok"] is False
    assert "/api-reference/authentication.md" not in result["missing"]
    assert "/api-reference/orders/modify-order.md" in result["missing"]


def test_required_docs_cover_safety_critical_surfaces():
    assert "/api-reference/rate-limits.md" in docs_check.REQUIRED_DOC_SUFFIXES
    assert "/api-reference/orders/create-order.md" in docs_check.REQUIRED_DOC_SUFFIXES
    assert "/api-reference/orders/preview-order.md" in docs_check.REQUIRED_DOC_SUFFIXES
    assert "/api-reference/orders/cancel-all-open-orders.md" in docs_check.REQUIRED_DOC_SUFFIXES
    assert "/api-reference/websocket/overview.md" in docs_check.REQUIRED_DOC_SUFFIXES
