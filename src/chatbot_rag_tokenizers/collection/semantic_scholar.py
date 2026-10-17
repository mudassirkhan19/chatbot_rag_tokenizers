"""Semantic Scholar client: bulk keyword search and a Seed's record, references and citations,
reading the Snapshot first.

API docs: https://api.semanticscholar.org/api-docs/graph (``/paper/search/bulk``,
``/paper/{id}``, ``/paper/{id}/references``, ``/paper/{id}/citations``)
Without a key, requests share a public pool and are often throttled with 429; with a key
(``S2_API_KEY``, sent as the ``x-api-key`` header) the limit is one request per second.
"""

import json
import os
import re
import sys
from collections.abc import Callable
from datetime import UTC, datetime

from .editions import Edition
from .http import RateLimitedHttp
from .snapshot import SnapshotStore

GRAPH_URL = "https://api.semanticscholar.org/graph/v1/paper"
API_URL = f"{GRAPH_URL}/search/bulk"
FIELDS = "paperId,externalIds,url,title,abstract,venue,year,authors"
MIN_INTERVAL_SECONDS = 1.0
# The shared pool can refuse every request for many minutes. Backoff doubles from 1 s up to
# 5 min, so 16 attempts wait out about 38 min of throttling before a run gives up.
MAX_ATTEMPTS = 16
MAX_BACKOFF_SECONDS = 300.0
API_KEY_ENV = "S2_API_KEY"
# References and citations come in pages of up to 1,000, and the API refuses any page that
# would reach past the 10,000th entry ("offset + limit must be < 10000").
LINK_PAGE_SIZE = 1000
MAX_LINKS = 9999

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


def _parse_seed(body: str) -> Edition:
    paper = json.loads(body)
    if not paper.get("paperId"):
        raise SemanticScholarError(f"Semantic Scholar returned no paper: {body[:200]}")
    return _parse_paper(paper)


def _parse_links(body: str, linked: str) -> tuple[int | None, list[Edition]]:
    """The next offset and the Editions on one references or citations page.

    ``linked`` is ``citedPaper`` or ``citingPaper``. Entries Semantic Scholar couldn't resolve
    to a paper have no paperId and are skipped.
    """
    page = json.loads(body)
    if "data" not in page:
        raise SemanticScholarError(f"Semantic Scholar returned no data: {body[:200]}")
    # Null when the publisher withholds the list (e.g. IEEE references): an empty page.
    papers = [entry.get(linked) or {} for entry in page["data"] or []]
    return page.get("next"), [_parse_paper(paper) for paper in papers if paper.get("paperId")]


class SemanticScholarSource:
    def __init__(self, snapshot: SnapshotStore, fields_of_study: str) -> None:
        self.snapshot = snapshot
        self.fields_of_study = fields_of_study
        self._http: RateLimitedHttp | None = None  # created on the first Snapshot miss

    def _search_request(self, query: str, token: str | None) -> dict:
        # The default paperId order is the one the API says stays stable while data changes.
        params = {"query": query, "fields": FIELDS}
        if self.fields_of_study:
            params["fieldsOfStudy"] = self.fields_of_study
        params["sort"] = "paperId:asc"
        if token is not None:
            params["token"] = token
        return {"source": "semantic-scholar", "url": API_URL, "params": params}

    def _load(self, request: dict, parse: Callable[[str], object], label: str) -> str:
        """The body for ``request``, from the Snapshot or fetched and stored once ``parse`` accepts it."""
        stored = self.snapshot.load(request)
        if stored is not None:
            return stored.body
        if self._http is None:
            self._http = RateLimitedHttp(MIN_INTERVAL_SECONDS, max_attempts=MAX_ATTEMPTS, max_backoff=MAX_BACKOFF_SECONDS)
        key = os.environ.get(API_KEY_ENV)
        # The key travels only as a header, never in the request description the Snapshot stores.
        headers = {"x-api-key": key} if key else None
        print(f"  semantic-scholar: fetching {label}", file=sys.stderr)
        body = self._http.get(request["url"], request["params"], headers=headers)
        parse(body)  # never store a response that can't be parsed
        collected_at = datetime.now(UTC).date().isoformat()
        return self.snapshot.save(request, body, collected_at).body

    def _search_page(self, query: str, token: str | None) -> tuple[str | None, list[Edition]]:
        page = "next page" if token is not None else "first page"
        return _parse_page(self._load(self._search_request(query, token), _parse_page, f"{page} for {query!r}"))

    def search(self, query: str) -> list[Edition]:
        """Every Edition ``query`` finds, following continuation tokens to the last page."""
        token, editions = self._search_page(query, None)
        while token is not None:
            token, found = self._search_page(query, token)
            editions.extend(found)
        return editions

    def paper(self, paper: str) -> Edition:
        """The Edition Semantic Scholar's record for ``paper`` (e.g. ``ARXIV:1508.07909``) stands for."""
        request = {"source": "semantic-scholar", "url": f"{GRAPH_URL}/{paper}", "params": {"fields": FIELDS}}
        return _parse_seed(self._load(request, _parse_seed, f"record of {paper}"))

    def references(self, paper: str) -> list[Edition]:
        """Every resolvable paper in ``paper``'s bibliography."""
        return self._links(paper, "references", "citedPaper")

    def citations(self, paper: str) -> list[Edition]:
        """Every resolvable paper that cites ``paper``, up to the API's limit of 9,999."""
        return self._links(paper, "citations", "citingPaper")

    def _links(self, paper: str, kind: str, linked: str) -> list[Edition]:
        def parse(body: str) -> tuple[int | None, list[Edition]]:
            return _parse_links(body, linked)

        editions: list[Edition] = []
        offset: int | None = 0
        while offset is not None:
            if offset >= MAX_LINKS:
                print(f"  semantic-scholar: {kind} of {paper} stop at the API's limit of {MAX_LINKS}", file=sys.stderr)
                break
            limit = min(LINK_PAGE_SIZE, MAX_LINKS - offset)
            params = {"fields": FIELDS, "offset": offset, "limit": limit}
            request = {"source": "semantic-scholar", "url": f"{GRAPH_URL}/{paper}/{kind}", "params": params}
            offset, found = parse(self._load(request, parse, f"{kind} of {paper} from {offset}"))
            editions.extend(found)
        return editions
