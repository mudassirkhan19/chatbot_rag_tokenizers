"""arXiv API client: pages through one keyword query, reading the Snapshot before the network.

API manual: https://info.arxiv.org/help/api/user-manual.html
Terms of use: at most one request every three seconds, one connection at a time.
"""

import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Callable
from datetime import UTC, datetime

from .editions import Edition
from .http import RateLimitedHttp
from .snapshot import SnapshotStore, StoredResponse

API_URL = "https://export.arxiv.org/api/query"
MIN_INTERVAL_SECONDS = 3.0
MAX_RESULTS_PER_QUERY = 30_000  # the API refuses to page past this
EMPTY_PAGE_RETRIES = 3

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
    "arxiv": "http://arxiv.org/schemas/atom",
}


class ArxivError(RuntimeError):
    pass


def _text(element: ET.Element, path: str) -> str:
    found = element.find(path, NS)
    if found is None or found.text is None:
        return ""
    return " ".join(found.text.split())


def _parse_entry(entry: ET.Element) -> Edition:
    abs_url = _text(entry, "atom:id")
    edition_id = abs_url.split("/abs/", 1)[1]
    return Edition(
        edition_id=edition_id,
        edition_kind="arxiv-preprint",
        title=_text(entry, "atom:title"),
        abstract=_text(entry, "atom:summary"),
        authors=[_text(author, "atom:name") for author in entry.findall("atom:author", NS)],
        year=_text(entry, "atom:published")[:4],
        arxiv_comments=_text(entry, "arxiv:comment"),
        journal_ref=_text(entry, "arxiv:journal_ref"),
        source_link=f"https://arxiv.org/abs/{edition_id}",
        arxiv_id=re.sub(r"v\d+$", "", edition_id),
        doi=_text(entry, "arxiv:doi"),
    )


def _parse_page(body: str) -> tuple[int, list[Edition]]:
    feed = ET.fromstring(body)
    entries = feed.findall("atom:entry", NS)
    # The API reports a malformed query as a single entry whose id points at its errors page.
    if len(entries) == 1 and "/api/errors" in _text(entries[0], "atom:id"):
        raise ArxivError(f"arXiv rejected the query: {_text(entries[0], 'atom:summary')}")
    total = int(_text(feed, "opensearch:totalResults") or 0)
    return total, [_parse_entry(entry) for entry in entries]


class ArxivSource:
    def __init__(
        self,
        snapshot: SnapshotStore,
        page_size: int,
        http_factory: Callable[[], RateLimitedHttp] = lambda: RateLimitedHttp(MIN_INTERVAL_SECONDS),
    ) -> None:
        self.snapshot = snapshot
        self.page_size = page_size
        self._http_factory = http_factory
        self._http: RateLimitedHttp | None = None

    def _request(self, query: str, start: int) -> dict:
        # Ascending submission date keeps earlier pages stable while new papers arrive at the end.
        return {
            "source": "arxiv",
            "url": API_URL,
            "params": {
                "search_query": query,
                "start": start,
                "max_results": self.page_size,
                "sortBy": "submittedDate",
                "sortOrder": "ascending",
            },
        }

    def _page(self, query: str, start: int) -> tuple[int, list[Edition]]:
        request = self._request(query, start)
        stored = self.snapshot.load(request)
        if stored is None:
            stored = self._fetch(request, start)
        return _parse_page(stored.body)

    def _fetch(self, request: dict, start: int) -> StoredResponse:
        if self._http is None:
            self._http = self._http_factory()
        for _ in range(EMPTY_PAGE_RETRIES):
            print(f"  arxiv: fetching results {start}+ for {request['params']['search_query']!r}", file=sys.stderr)
            body = self._http.get(request["url"], request["params"])
            total, editions = _parse_page(body)
            # arXiv sometimes returns an empty page mid-query; never store one as if it were the answer.
            if editions or start >= total:
                collected_at = datetime.now(UTC).date().isoformat()
                return self.snapshot.save(request, body, collected_at)
        raise ArxivError(f"arXiv kept returning an empty page at start={start} of {total}")

    def search(self, query: str) -> list[Edition]:
        """All results for ``query``, in API order, possibly with repeats across pages."""
        total, editions = self._page(query, 0)
        for start in range(self.page_size, min(total, MAX_RESULTS_PER_QUERY), self.page_size):
            editions.extend(self._page(query, start)[1])
        return editions
