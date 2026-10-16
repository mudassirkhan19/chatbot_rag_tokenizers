"""Semantic Scholar bulk search client: pages through one keyword query, reading the Snapshot first.

API docs: https://api.semanticscholar.org/api-docs/graph (``/paper/search/bulk``)
Without a key, requests share a public pool and are often throttled with 429; with a key
(``S2_API_KEY``, sent as the ``x-api-key`` header) the limit is one request per second.
"""

import json
import os
import re
import sys
from datetime import UTC, datetime

from .editions import Edition
from .http import RateLimitedHttp
from .snapshot import SnapshotStore, StoredResponse

API_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = "paperId,externalIds,url,title,abstract,venue,year,authors"
MIN_INTERVAL_SECONDS = 1.0
# The shared pool throttles hard; backoff doubles from 1 s, capped by RateLimitedHttp.
MAX_ATTEMPTS = 12
API_KEY_ENV = "S2_API_KEY"

# arXiv mints DataCite DOIs for its preprints; Semantic Scholar sometimes reports only that.
ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)


class SemanticScholarError(RuntimeError):
    pass


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _parse_paper(paper: dict) -> Edition:
    ids = paper.get("externalIds") or {}
    doi = ids.get("DOI") or ""
    arxiv_id = ids.get("ArXiv") or ""
    if not arxiv_id and (match := ARXIV_DOI.match(doi)):
        arxiv_id = match.group(1)
    acl_id = ids.get("ACL") or ""
    s2_id = paper["paperId"]
    common = dict(
        title=_clean(paper.get("title")),
        abstract=_clean(paper.get("abstract")),
        authors=[_clean(author.get("name")) for author in paper.get("authors") or []],
        year=str(paper.get("year") or ""),
        arxiv_id=arxiv_id,
        doi=doi,
        acl_id=acl_id,
        s2_id=s2_id,
    )
    if arxiv_id:
        # A record with an arXiv id is read as the preprint Edition. Its venue is left empty:
        # Semantic Scholar's venue belongs to the venue Edition it has merged into the record.
        return Edition(
            edition_id=arxiv_id,
            edition_kind="arxiv-preprint",
            source_link=f"https://arxiv.org/abs/{arxiv_id}",
            **common,
        )
    if acl_id:
        edition_id, link = acl_id, f"https://aclanthology.org/{acl_id}"
    elif doi:
        edition_id, link = doi, f"https://doi.org/{doi}"
    else:
        edition_id, link = s2_id, paper.get("url") or f"https://www.semanticscholar.org/paper/{s2_id}"
    return Edition(
        edition_id=edition_id,
        edition_kind="venue",
        venue=_clean(paper.get("venue")),
        source_link=link,
        **common,
    )


def _parse_page(body: str) -> tuple[str | None, list[Edition]]:
    page = json.loads(body)
    if "data" not in page:
        raise SemanticScholarError(f"Semantic Scholar returned no data: {body[:200]}")
    return page.get("token"), [_parse_paper(paper) for paper in page["data"]]


class SemanticScholarSource:
    def __init__(self, snapshot: SnapshotStore, fields_of_study: str) -> None:
        self.snapshot = snapshot
        self.fields_of_study = fields_of_study
        self._http: RateLimitedHttp | None = None  # created on the first Snapshot miss

    def _request(self, query: str, token: str | None) -> dict:
        # The default paperId order is the one the API says stays stable while data changes.
        params = {"query": query, "fields": FIELDS}
        if self.fields_of_study:
            params["fieldsOfStudy"] = self.fields_of_study
        params["sort"] = "paperId:asc"
        if token is not None:
            params["token"] = token
        return {"source": "semantic-scholar", "url": API_URL, "params": params}

    def _page(self, query: str, token: str | None) -> tuple[str | None, list[Edition]]:
        request = self._request(query, token)
        stored = self.snapshot.load(request)
        if stored is None:
            stored = self._fetch(request)
        return _parse_page(stored.body)

    def _fetch(self, request: dict) -> StoredResponse:
        if self._http is None:
            self._http = RateLimitedHttp(MIN_INTERVAL_SECONDS, max_attempts=MAX_ATTEMPTS)
        key = os.environ.get(API_KEY_ENV)
        # The key travels only as a header, never in the request description the Snapshot stores.
        headers = {"x-api-key": key} if key else None
        page = "next page" if "token" in request["params"] else "first page"
        print(f"  semantic-scholar: fetching {page} for {request['params']['query']!r}", file=sys.stderr)
        body = self._http.get(request["url"], request["params"], headers=headers)
        _parse_page(body)  # never store a response that isn't a results page
        collected_at = datetime.now(UTC).date().isoformat()
        return self.snapshot.save(request, body, collected_at)

    def search(self, query: str) -> list[Edition]:
        """Every Edition ``query`` finds, following continuation tokens to the last page."""
        token, editions = self._page(query, None)
        while token is not None:
            token, found = self._page(query, token)
            editions.extend(found)
        return editions
