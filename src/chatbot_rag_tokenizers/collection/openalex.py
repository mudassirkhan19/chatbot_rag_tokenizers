"""OpenAlex works client: pages through one keyword query with a cursor, reading the Snapshot first.

API docs: https://help.openalex.org/how-to-use-the-api (works, search, paging, rate limits)
Following ``next_cursor`` past the first page needs a free key (``OPENALEX_API_KEY``, sent as a
bearer token). A search with more than five boolean operators is limited to five requests per
second with a key.
"""

import json
import os
import re
import sys
from datetime import UTC, datetime

from .editions import Edition
from .http import RateLimitedHttp
from .snapshot import SnapshotStore, StoredResponse

API_URL = "https://api.openalex.org/works"
FIELDS = (
    "id,doi,ids,title,publication_year,type,authorships,abstract_inverted_index,"
    "primary_location,locations,best_oa_location"
)
PER_PAGE = 100  # the documented maximum
MIN_INTERVAL_SECONDS = 0.25  # under the 5 per second allowed for queries with many operators
API_KEY_ENV = "OPENALEX_API_KEY"

DOI_URL = re.compile(r"^https?://(dx\.)?doi\.org/", re.IGNORECASE)
# How OpenAlex names an arXiv location: its OAI-PMH id, its abstract page or arXiv's DataCite DOI.
ARXIV_OAI_ID = re.compile(r"^pmh:oai:arxiv\.org:(.+)$", re.IGNORECASE)
ARXIV_ABS_URL = re.compile(r"^https?://(?:www\.)?arxiv\.org/abs/(.+)$", re.IGNORECASE)
ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)
VERSION_SUFFIX = re.compile(r"v\d+$")


class OpenAlexError(RuntimeError):
    pass


def _clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _bare_doi(url: str | None) -> str:
    return DOI_URL.sub("", url or "")


def _abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """OpenAlex ships abstracts as word → positions; put the words back in order."""
    positions = {pos: word for word, places in (inverted_index or {}).items() for pos in places}
    return _clean(" ".join(positions[pos] for pos in sorted(positions)))


def _arxiv_id(work: dict) -> str:
    """The arXiv id of the preprint OpenAlex lists among the work's locations, without its Version."""
    for location in work.get("locations") or []:
        for pattern, value in [
            (ARXIV_OAI_ID, location.get("id")),
            (ARXIV_ABS_URL, location.get("landing_page_url")),
            (ARXIV_DOI, _bare_doi(location.get("doi"))),
        ]:
            if value and (match := pattern.match(value)):
                return VERSION_SUFFIX.sub("", match.group(1))
    if match := ARXIV_DOI.match(_bare_doi(work.get("doi"))):
        return VERSION_SUFFIX.sub("", match.group(1))
    return ""


def _oa_pdf_urls(work: dict) -> list[str]:
    """Every open-access PDF the work lists, OpenAlex's best one first."""
    best = work.get("best_oa_location")
    locations = [best, *(work.get("locations") or [])] if best else work.get("locations") or []
    urls: list[str] = []
    for location in locations:
        url = location.get("pdf_url")
        if location.get("is_oa") and url and url not in urls:
            urls.append(url)
    return urls


def _parse_work(work: dict) -> Edition:
    openalex_id = work["id"].rsplit("/", 1)[-1]
    doi = _bare_doi(work.get("doi"))
    arxiv_id = _arxiv_id(work)
    primary = work.get("primary_location") or {}
    common = dict(
        title=_clean(work.get("title")),
        abstract=_abstract(work.get("abstract_inverted_index")),
        authors=[_clean((a.get("author") or {}).get("display_name")) for a in work.get("authorships") or []],
        year=str(work.get("publication_year") or ""),
        arxiv_id=arxiv_id,
        doi=doi,
        openalex_id=openalex_id,
        openalex_type=work.get("type") or "",
        openalex_raw_type=_clean(primary.get("raw_type")),
        openalex_raw_source_name=_clean(primary.get("raw_source_name")),
    )
    if arxiv_id:
        # Like a Semantic Scholar record, an OpenAlex work merges a Work's Editions. One with an
        # arXiv location is read as the preprint; its venue and PDFs belong to the venue Edition.
        return Edition(
            edition_id=arxiv_id,
            edition_kind="arxiv-preprint",
            source_link=f"https://arxiv.org/abs/{arxiv_id}",
            **common,
        )
    source = primary.get("source") or {}
    return Edition(
        edition_id=doi or openalex_id,
        edition_kind="venue",
        venue=_clean(source.get("display_name")),
        source_link=f"https://doi.org/{doi}" if doi else f"https://openalex.org/{openalex_id}",
        oa_pdf_urls=_oa_pdf_urls(work),
        **common,
    )


def _parse_page(body: str) -> tuple[str | None, list[Edition]]:
    page = json.loads(body)
    if "results" not in page:
        raise OpenAlexError(f"OpenAlex returned no results: {body[:200]}")
    editions = [_parse_work(work) for work in page["results"]]
    # The last page has no next cursor; a page past the end has no results.
    cursor = (page.get("meta") or {}).get("next_cursor") if editions else None
    return cursor, editions


class OpenAlexSource:
    def __init__(self, snapshot: SnapshotStore) -> None:
        self.snapshot = snapshot
        self._http: RateLimitedHttp | None = None  # created on the first Snapshot miss

    def _request(self, query: str, cursor: str) -> dict:
        # A fixed sort, so a fresh fetch pages in the same order; the cursor breaks ties by work id.
        params = {
            "search.title_and_abstract": query,
            "select": FIELDS,
            "sort": "publication_date:asc",
            "per_page": PER_PAGE,
            "cursor": cursor,
        }
        return {"source": "openalex", "url": API_URL, "params": params}

    def _page(self, query: str, cursor: str) -> tuple[str | None, list[Edition]]:
        request = self._request(query, cursor)
        stored = self.snapshot.load(request)
        if stored is None:
            stored = self._fetch(request)
        return _parse_page(stored.body)

    def _fetch(self, request: dict) -> StoredResponse:
        key = os.environ.get(API_KEY_ENV)
        if not key:
            raise OpenAlexError(
                f"{API_KEY_ENV} is not set and the Snapshot has no OpenAlex page for "
                f"{request['params']['search.title_and_abstract']!r}. Get a free key at "
                "https://openalex.org/settings/api, or switch OpenAlex off with "
                "`enabled = false` under [sources.openalex]."
            )
        if self._http is None:
            self._http = RateLimitedHttp(MIN_INTERVAL_SECONDS)
        # The key travels only as a header, never in the request description the Snapshot stores.
        headers = {"Authorization": f"Bearer {key}"}
        page = "first page" if request["params"]["cursor"] == "*" else "next page"
        query = request["params"]["search.title_and_abstract"]
        print(f"  openalex: fetching {page} for {query!r}", file=sys.stderr)
        body = self._http.get(request["url"], request["params"], headers=headers)
        _parse_page(body)  # never store a response that isn't a results page
        collected_at = datetime.now(UTC).date().isoformat()
        return self.snapshot.save(request, body, collected_at)

    def search(self, query: str) -> list[Edition]:
        """Every Edition ``query`` finds, following cursors to the last page."""
        cursor, editions = self._page(query, "*")
        while cursor is not None:
            cursor, found = self._page(query, cursor)
            editions.extend(found)
        return editions
