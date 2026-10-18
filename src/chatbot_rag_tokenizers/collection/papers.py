"""The `not a paper` stage of the Relevance verdict: the corpus keeps only journal, conference and
workshop papers and preprints, so Editions whose source metadata says they are something else are
excluded before the judge (ADR 0040)."""

import re

from .editions import Edition

CRAN_PACKAGE_DOI = re.compile(r"^10\.32614/cran\.package\.", re.IGNORECASE)
# Paper number 0 of an ACL volume is its front matter: 2025.wnut-1.0 in new-style IDs, and in
# old-style ones W18-1200 (workshops: a two-digit volume and paper) or P16-1000 (a one-digit
# volume and three-digit paper).
ACL_FRONT_MATTER = re.compile(r"^(?:\d{4}\.[a-z0-9-]+\.0|W\d{2}-\d{2}00|[A-VX-Z]\d{2}-\d000)$")
# OpenAlex work types that never name a paper. Kept are article, preprint, conference-paper,
# book-chapter (how Springer records many LNCS papers), review, report, data-paper,
# software-paper and other (which also holds conference papers).
NOT_PAPER_OPENALEX_TYPES = {
    "book",
    "conference-abstract",
    "dataset",
    "dissertation",
    "editorial",
    "erratum",
    "grant",
    "letter",
    "libguides",
    "paratext",
    "peer-review",
    "reference-entry",
    "retraction",
    "software",
    "standard",
    "supplementary-materials",
}
# The degree a repository's citation of a thesis names, as in "…, Doctor of Philosophy, Universiteit
# van Amsterdam." OpenAlex can type such a thesis "other".
DEGREE = re.compile(r"\b(?:Doctor of Philosophy|Master of (?:Science|Arts|Philosophy)|Bachelor of (?:Science|Arts))\b")

# Semantic Scholar's responses in the Snapshot carry no publication type, so for its records only
# the title tells: "… [R package wordpiece version 1.0.2]", or a whole proceedings volume, whose
# title starts "Proceedings of" or ends "Proceedings of the Second Workshop". A paper's cover page
# ("This paper is included in the Proceedings of the 33rd USENIX …") is neither.
R_PACKAGE_TITLE = re.compile(r"\[R package\b", re.IGNORECASE)
PROCEEDINGS_TITLE = re.compile(r"^Proceedings of\b|\bProceedings of the \w+ Workshop$", re.IGNORECASE)

# arXiv records no document type, but authors say so in the comments: "PhD thesis", "MSc Thesis,
# 44 pages", "A dissertation submitted to …", "… preprint. Textbook for senior undergraduates".
# Only a clause that starts with it counts, so "technical report, extraction from PhD thesis"
# stays a paper.
CLAUSE_START = r"(?:^|[.;,:(]\s*)(?:an?\s+)?"
DEGREE_WORD = r"(?:Ph\.?\s?D\.?|doctoral|M\.?Sc\.?|M\.?S\.?|M\.?A\.?|master['’]?s|B\.?Sc\.?|B\.?A\.?|bachelor['’]?s|honou?rs|undergraduate)"
THESIS_COMMENT = re.compile(rf"{CLAUSE_START}(?:{DEGREE_WORD}\s+)?(?:thesis|dissertation)\b", re.IGNORECASE)
TEXTBOOK_COMMENT = re.compile(rf"{CLAUSE_START}textbook\b", re.IGNORECASE)


def not_a_paper(edition: Edition) -> str:
    """Why ``edition`` is not a paper, or "" when nothing its sources recorded says so."""
    if CRAN_PACKAGE_DOI.match(edition.doi):
        return f"not a paper: a CRAN package manual (DOI {edition.doi})"
    if edition.edition_kind == "venue" and ACL_FRONT_MATTER.match(edition.acl_id):
        return f"not a paper: {edition.acl_id} is the front matter of an ACL volume"
    if edition.openalex_type in NOT_PAPER_OPENALEX_TYPES:
        return f"not a paper: OpenAlex type {edition.openalex_type}"
    if match := DEGREE.search(edition.openalex_raw_source_name):
        return f"not a paper: a thesis, its repository record names a {match.group(0)}"
    if edition.openalex_raw_type == "Audiovisual":
        return "not a paper: a recording, its DataCite resource type is Audiovisual"
    if THESIS_COMMENT.search(edition.arxiv_comments):
        return f"not a paper: a thesis, by its arXiv comments: {edition.arxiv_comments}"
    if TEXTBOOK_COMMENT.search(edition.arxiv_comments):
        return f"not a paper: a textbook, by its arXiv comments: {edition.arxiv_comments}"
    if R_PACKAGE_TITLE.search(edition.title):
        return "not a paper: an R package manual, by its title"
    if PROCEEDINGS_TITLE.search(edition.title):
        return "not a paper: a proceedings volume, by its title"
    return ""
