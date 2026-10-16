"""ACL Anthology client: one paper page per ACL ID, reading the Snapshot first.

The paper page is the only per-paper export with the abstract, the PDF link, the venue and
the publisher together: the BibTeX and MODS exports leave out the abstract and the venue, and
the repository's XML files hold a whole collection each (several MB). The page carries the
``citation_*`` meta tags that the Anthology publishes for indexers, plus a details list.

Site: https://aclanthology.org/ (no published rate limit; we wait 1 s between requests)
Licences: https://aclanthology.org/faq/copyright/
"""

import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser

from .http import RateLimitedHttp
from .snapshot import SnapshotStore, StoredResponse

SITE = "https://aclanthology.org"
MIN_INTERVAL_SECONDS = 1.0
# Some Anthology volumes misspell ACL's name.
ACL_PUBLISHERS = {"Association for Computational Linguistics", "Association for Computational Lingustics"}
# The Anthology's licences cover ACL materials only: CC BY-NC-SA 3.0 before 2016, CC BY 4.0 since.
CC_BY = "https://creativecommons.org/licenses/by/4.0/"
CC_BY_NC_SA = "https://creativecommons.org/licenses/by-nc-sa/3.0/"
NOT_FOUND = ""  # the stored body of a page the Anthology doesn't have


class AclAnthologyError(RuntimeError):
    pass


@dataclass(frozen=True)
class AclRecord:
    acl_id: str
    title: str
    authors: list[str]
    abstract: str  # empty when the Anthology has none, as for many older papers
    year: str
    venues: list[str]  # the Anthology's venue names, e.g. "Annual Meeting of the Association for …"
    publisher: str
    doi: str
    pdf_link: str  # empty when the Anthology hosts no PDF

    @property
    def licence(self) -> str:
        if self.publisher not in ACL_PUBLISHERS or not self.year.isdigit():
            return "unknown"
        return CC_BY if int(self.year) >= 2016 else CC_BY_NC_SA

    @property
    def source_link(self) -> str:
        return f"{SITE}/{self.acl_id}"


def _clean(text: str) -> str:
    return " ".join(text.split())


class _PaperPage(HTMLParser):
    """Collects the citation_* meta tags, the abstract and the details list of a paper page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.details: dict[str, str] = {}
        self.venues: list[str] = []
        self.abstract = ""
        self._in_abstract_card = False
        self._capture: str | None = None  # "abstract", "dt" or "dd"
        self._text: list[str] = []
        self._term = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name: value or "" for name, value in attrs}
        if tag == "meta" and attr.get("name", "").startswith("citation_"):
            self.meta.setdefault(attr["name"], []).append(_clean(attr.get("content", "")))
        elif tag == "div" and "acl-abstract" in attr.get("class", "").split():
            self._in_abstract_card = True
        elif tag == "span" and self._in_abstract_card and self._capture is None:
            self._start("abstract")
        elif tag in ("dt", "dd"):
            self._start(tag)
        elif tag == "a" and self._capture == "dd" and self._term in ("Venue", "Venues") and attr.get("title"):
            self.venues.append(_clean(attr["title"]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "span" and self._capture == "abstract":
            self.abstract = self._stop()
            self._in_abstract_card = False
        elif tag == "dt" and self._capture == "dt":
            self._term = self._stop().rstrip(":")
        elif tag == "dd" and self._capture == "dd":
            self.details.setdefault(self._term, self._stop())

    def handle_data(self, data: str) -> None:
        if self._capture is not None:
            self._text.append(data)

    def _start(self, what: str) -> None:
        self._capture, self._text = what, []

    def _stop(self) -> str:
        self._capture = None
        return _clean("".join(self._text))


def _first(page: _PaperPage, name: str) -> str:
    return page.meta.get(name, [""])[0]


def _parse_page(acl_id: str, body: str) -> AclRecord | None:
    if body == NOT_FOUND:
        return None
    page = _PaperPage()
    page.feed(body)
    page.close()
    if page.details.get("Anthology ID") != acl_id or "citation_title" not in page.meta:
        raise AclAnthologyError(f"ACL Anthology page for {acl_id} is not a paper page for that ID")
    return AclRecord(
        acl_id=acl_id,
        title=_first(page, "citation_title"),
        authors=page.meta.get("citation_author", []),
        abstract=page.abstract,
        year=page.details.get("Year", ""),
        venues=page.venues,
        publisher=page.details.get("Publisher", ""),
        doi=_first(page, "citation_doi") or page.details.get("DOI", ""),
        pdf_link=_first(page, "citation_pdf_url"),
    )


class AclAnthologySource:
    def __init__(self, snapshot: SnapshotStore) -> None:
        self.snapshot = snapshot
        self._http: RateLimitedHttp | None = None  # created on the first Snapshot miss

    def _request(self, acl_id: str) -> dict:
        return {"source": "acl-anthology", "url": f"{SITE}/{acl_id}/", "params": {}}

    def record(self, acl_id: str) -> AclRecord | None:
        """The ACL Edition's metadata, or None when the Anthology has no paper with this ID."""
        request = self._request(acl_id)
        stored = self.snapshot.load(request)
        if stored is None:
            stored = self._fetch(acl_id, request)
        return _parse_page(acl_id, stored.body)

    def _fetch(self, acl_id: str, request: dict) -> StoredResponse:
        if self._http is None:
            self._http = RateLimitedHttp(MIN_INTERVAL_SECONDS)
        response = self._http.response(request["url"], request["params"])
        # Sources sometimes report an ACL ID the Anthology doesn't have, or the ID of a whole
        # proceedings volume, which redirects to its volume page; remember either miss.
        if response.status_code == 404:
            print(f"  acl-anthology: no paper {acl_id}", file=sys.stderr)
            body = NOT_FOUND
        elif response.url.path.startswith("/volumes/"):
            print(f"  acl-anthology: {acl_id} is a volume, not a paper", file=sys.stderr)
            body = NOT_FOUND
        else:
            response.raise_for_status()
            body = response.text
            _parse_page(acl_id, body)  # never store a page that isn't this paper's
        collected_at = datetime.now(UTC).date().isoformat()
        return self.snapshot.save(request, body, collected_at)
