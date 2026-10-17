"""The common Edition record that every source's results are normalised into."""

import re
from dataclasses import dataclass, field

# ACL mints its DOIs from the ACL ID, but sources disagree on their case (Semantic Scholar
# upper-cases them). Old-style ACL IDs (P16-1162) are upper-case, new-style ones
# (2020.findings-emnlp.414) lower-case.
ACL_DOI = re.compile(r"^10\.18653/v1/(.+)$", re.IGNORECASE)
OLD_STYLE_ACL_ID = re.compile(r"^[a-z]\d{2}-\d{4}$", re.IGNORECASE)


@dataclass
class Edition:
    edition_id: str  # pinned, e.g. "2106.12345v3"; an ACL ID, DOI or S2 id for a venue Edition
    edition_kind: str  # "arxiv-preprint" or "venue"
    title: str
    abstract: str
    authors: list[str]
    year: str
    venue: str = ""
    arxiv_comments: str = ""
    journal_ref: str = ""
    source_link: str = ""
    pdf_link: str = ""  # ACL Anthology only, for now
    arxiv_id: str = ""
    doi: str = ""
    acl_id: str = ""
    s2_id: str = ""  # Semantic Scholar paperId
    openalex_id: str = ""  # OpenAlex work id, e.g. "W2885185669"
    oa_pdf_urls: list[str] = field(default_factory=list)  # venue Editions only: open-access PDFs, best first
    licence: str = "unknown"
    versions: list[tuple[str, str]] = field(default_factory=list)  # arXiv only: ("v1", ISO time), oldest first
    withdrawn: bool = False  # arXiv only: the latest Version is a withdrawal, from the full record
    discovery_channels: set[str] = field(default_factory=set)

    @property
    def version(self) -> int:
        """The pinned arXiv Version, or 0 when the source didn't report one."""
        _, sep, version = self.edition_id.rpartition("v")
        return int(version) if self.edition_kind == "arxiv-preprint" and sep and version.isdigit() else 0

    @property
    def reported_acl_id(self) -> str:
        """The ACL ID a source reported for this Edition, directly or as an ACL DOI (``10.18653/v1/<ACL ID>``)."""
        if self.acl_id:
            return self.acl_id
        if not (match := ACL_DOI.match(self.doi)):
            return ""
        acl_id = match.group(1)
        return acl_id.upper() if OLD_STYLE_ACL_ID.match(acl_id) else acl_id.lower()

    def match_keys(self) -> list[str]:
        """The exact identifiers that name this Edition and no other.

        A preprint is named only by its arXiv id: the DOI or ACL ID a source reports for a
        preprint belongs to its venue Edition, so matching on it would merge two Editions.
        DOIs are case-insensitive, and sources disagree on case.
        """
        if self.edition_kind == "arxiv-preprint":
            keys = [f"arxiv:{self.arxiv_id}"]
        else:
            keys = [f"acl:{self.acl_id}"] if self.acl_id else []
            if self.doi:
                keys.append(f"doi:{self.doi.lower()}")
        if self.s2_id:
            keys.append(f"s2:{self.s2_id}")
        if self.openalex_id:
            keys.append(f"openalex:{self.openalex_id}")
        return keys


def combine(kept: Edition, new: Edition) -> Edition:
    """Combine two Candidates that are the same Edition into one, keeping every Discovery channel.

    The newer pinned Version wins (a source without Versions never displaces one that has
    them), otherwise the Candidate found first does. The other only fills in what the winner
    lacks: external identifiers and, for a venue Edition, its venue and open-access PDFs. Its
    other descriptive fields describe the same Edition less well.
    """
    base, other = (new, kept) if new.version > kept.version else (kept, new)
    filled = ["arxiv_id", "doi", "acl_id", "s2_id", "openalex_id"]
    if base.edition_kind == "venue":
        filled += ["venue", "oa_pdf_urls"]
    for name in filled:
        if not getattr(base, name):
            setattr(base, name, getattr(other, name))
    base.discovery_channels |= other.discovery_channels
    return base
