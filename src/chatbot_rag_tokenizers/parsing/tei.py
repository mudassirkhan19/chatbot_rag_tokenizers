"""The TEI reader: turns GROBID's TEI into a structured document, applying the element rules (ADR 0028).

It reads only content that is the same on every parse of a file (ADR 0024): the title, the abstract,
each Section's head, sentences, block formulas and the pages they sit on, the tables and figure
captions, and the bibliography. GROBID's request timestamp, funders and figure graphics change between
parses and are never read.

GROBID gives Sections as a flat list of ``div``s, so each Section's path is rebuilt from its number:
3.1 sits under 3 when the paper has a Section 3, and directly under the title when GROBID lost that
heading. An unnumbered head (often a run-in paragraph heading) sits under the last numbered Section.
A numbered heading GROBID left in a body paragraph (at its start, as the whole paragraph, or at the end of
a sentence) is recovered as a Section of its own (``lost_headings``, ADR 0041).

The element rules (ADR 0028):
- Front matter other than the title and the abstract (authors, affiliations, funders) is not read.
- Block formulas join the paragraph before them, as GROBID renders their text.
- Acknowledgements are dropped, from ``back`` and from a ``body`` Section headed as such.
- Appendices are Sections with the appendix flag: the annex in ``back``, and a ``body`` Section
  headed with a letter from A to H ("A Grid search", "B.2 Data", "C. Examples") or "Appendix ..."
  after the numbered body, together with every
  Section after it. Appendix Sections take their number from the head's leading letter. An annex
  Section numbered like "5.4" under a body Section 5 is a body Section GROBID misplaced.
- Each table (with its caption and rows) and each figure caption is tied to one Section: the first
  that cites it by id, else the first that cites its printed number, else the one its page falls in.
- Reference lists give no Sections; the bibliography is read as structured references.
- Footnotes are not read: GROBID puts them outside every Section.
"""

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, field, replace

from .lost_headings import Typography, split_lost_headings

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ABSTRACT = "Abstract"
# A head that starts with an appendix letter and an optional number, e.g. "A Grid search", "B.2 Data",
# "C. Examples" (ICML prints a full stop after the letter).
APPENDIX_HEAD = re.compile(r"(?P<number>[A-Z](?:\.\d+)*)\.?\s+(?P<title>\S.*)")
APPENDIX_OPENERS = "ABCDEFGH"
# A subsection number such as "5.4": in the annex, one that continues a body Section is not an appendix.
SUBSECTION_NUMBER = re.compile(r"\d+(?:\.\d+)+")
APPENDIX_TITLE = re.compile(r"(appendix|appendices|supplementary materials?)\b.*", re.IGNORECASE)
ACKNOWLEDGEMENTS = re.compile(r"acknowledge?ments?", re.IGNORECASE)


class UnreadableTei(ValueError):
    """GROBID's answer can't be read as a document."""


@dataclass(frozen=True)
class Sentence:
    text: str
    pages: tuple[int, ...]  # 1-based pages the sentence sits on, in order


@dataclass(frozen=True)
class Paragraph:
    sentences: tuple[Sentence, ...]

    @property
    def text(self) -> str:
        return " ".join(sentence.text for sentence in self.sentences)

    @property
    def pages(self) -> tuple[int, ...]:
        return tuple(sorted({page for sentence in self.sentences for page in sentence.pages}))


@dataclass(frozen=True)
class Table:
    label: str  # as printed, e.g. "Table 2"
    caption: str
    rows: tuple[tuple[str, ...], ...]  # cell texts, row by row; a spanning cell is one cell
    pages: tuple[int, ...]


@dataclass(frozen=True)
class Caption:
    label: str  # as printed, e.g. "Figure 2"; "" when GROBID found none
    paragraph: Paragraph


@dataclass(frozen=True)
class Section:
    number: str  # as printed, e.g. "3.1" or "A.2"; "" when the head has none
    title: str
    path: tuple[str, ...]  # headings from the top-level Section down to this one, e.g. ("3 Method", "3.1 Data")
    appendix: bool
    paragraphs: tuple[Paragraph, ...]
    tables: tuple[Table, ...] = ()
    captions: tuple[Caption, ...] = ()


@dataclass(frozen=True)
class Reference:
    """One entry of a file's bibliography, as GROBID gives it."""

    key: str  # GROBID's id within the file, e.g. "b0"
    title: str
    authors: tuple[str, ...]
    year: str  # "" when GROBID found none
    identifiers: dict[str, str]  # e.g. {"DOI": "10.18653/...", "arXiv": "arXiv:1710.04087", "url": "..."}
    raw: str  # the reference as printed


@dataclass(frozen=True)
class Document:
    title: str
    grobid_version: str  # as the TEI header reports it, e.g. "0.9.1"
    sections: tuple[Section, ...]  # the abstract first, then the body in reading order, then the annex
    bibliography: tuple[Reference, ...] = ()


@dataclass
class _Draft:
    """A Section being read, with the figure and table citations its text makes."""

    section: Section
    refs: list[tuple[str, str, str]] = field(default_factory=list)  # (type, target, text) of each ref
    tables: list[Table] = field(default_factory=list)
    captions: list[Caption] = field(default_factory=list)

    def first_page(self) -> int | None:
        pages = [page for paragraph in self.section.paragraphs for page in paragraph.pages]
        return min(pages) if pages else None


def read_tei(tei: str) -> Document:
    """The document in GROBID's TEI. Raises UnreadableTei when it isn't well-formed TEI with a header."""
    try:
        root = ET.fromstring(tei)
    except ET.ParseError as error:
        raise UnreadableTei(str(error)) from error
    header = root.find("tei:teiHeader", NS)
    if header is None:
        raise UnreadableTei("no teiHeader")
    application = header.find(".//tei:appInfo/tei:application[@ident='GROBID']", NS)
    drafts = [_Draft(section) for section in _abstract(header)]
    body = root.findall("tei:text/tei:body/tei:div", NS)
    drafts += _SectionReader(Typography(body)).read(
        body,
        root.findall("tei:text/tei:back/tei:div[@type='annex']/tei:div", NS),
    )
    text = root.find("tei:text", NS)
    if text is not None:
        _place_figures(text, drafts)
    return Document(
        title=_text(header.find("tei:fileDesc/tei:titleStmt/tei:title[@type='main']", NS)),
        grobid_version=application.get("version", "") if application is not None else "",
        sections=tuple(replace(d.section, tables=tuple(d.tables), captions=tuple(d.captions)) for d in drafts),
        bibliography=tuple(_references(root.findall("tei:text/tei:back//tei:listBibl/tei:biblStruct", NS))),
    )


def _abstract(header: ET.Element) -> Iterator[Section]:
    paragraphs = _paragraphs(header.findall("tei:profileDesc/tei:abstract//tei:p", NS))
    if paragraphs:
        yield Section(number="", title=ABSTRACT, path=(ABSTRACT,), appendix=False, paragraphs=paragraphs)


class _SectionReader:
    """Reads the body and annex ``div``s into Sections, keeping the state the paths and rules need."""

    def __init__(self, typography: Typography) -> None:
        self.typography = typography  # how the body prints its lines and headings, to find the headings GROBID lost
        self.drafts: list[_Draft] = []
        self.headings: dict[str, str] = {}  # Section number -> its heading, for the paths of the Sections under it
        self.body_headings: dict[str, str] = {}  # the body's headings, kept when the appendix starts
        self.last_numbered: tuple[str, ...] = ()  # path of the last numbered Section
        self.last_number = ""  # number of the last numbered body Section, e.g. "3.1"
        self.numbered_body = False  # the body has had a numbered Section
        self.appendix = False
        self.dropping = False  # inside the acknowledgements: headless divs after them are dropped too

    def read(self, body: list[ET.Element], annex: list[ET.Element]) -> list[_Draft]:
        for div in body:
            # Appendices number with letters, so a lost numbered heading is looked for only before them.
            for part in [div] if self.appendix else split_lost_headings(div, self.last_number, self.typography):
                self._div(part, in_annex=False)
        if annex:
            self.dropping = False
            self._start_appendix()
        for div in annex:
            self._div(div, in_annex=True)
        return self.drafts

    def _start_appendix(self) -> None:
        # Appendices number their own Sections: "A.1" never sits under a body Section.
        self.appendix = True
        self.body_headings = self.body_headings or self.headings
        self.headings = {}
        self.last_numbered = ()

    def _div(self, div: ET.Element, in_annex: bool) -> None:
        paragraphs = _div_paragraphs(div)
        refs = [(ref.get("type", ""), ref.get("target", ""), _text(ref)) for ref in div.iter(f"{TEI}ref")]
        head = div.find("tei:head", NS)
        if head is None:
            # A div without a head continues the Section before it.
            if self.dropping:
                return
            if self.drafts:
                previous = self.drafts[-1]
                previous.section = replace(previous.section, paragraphs=previous.section.paragraphs + paragraphs)
                previous.refs += refs
            elif paragraphs:
                section = Section(number="", title="", path=(), appendix=self.appendix, paragraphs=paragraphs)
                self.drafts.append(_Draft(section, refs))
            return
        number = (head.get("n") or "").strip()
        title = _text(head)
        self.dropping = bool(ACKNOWLEDGEMENTS.fullmatch(title.rstrip(".: ")))
        if self.dropping:
            return
        misplaced = False  # a body Section GROBID put in the annex
        if not number:
            number, title = self._appendix_number(title, in_annex)
        elif not self.appendix:
            self.numbered_body = True
            self.last_number = number.rstrip(".")
        else:
            misplaced = bool(SUBSECTION_NUMBER.fullmatch(number)) and _parent_numbers(number)[0] in self.body_headings
        appendix = self.appendix and not misplaced
        headings = self.body_headings if misplaced else self.headings
        if number:
            heading = f"{number} {title}"
            parents = _parent_numbers(number)
            path = tuple(headings[parent] for parent in parents if parent in headings) + (heading,)
            headings[number.rstrip(".")] = heading
            self.last_numbered = path
        else:
            path = self.last_numbered + (title,)
        section = Section(number=number, title=title, path=path, appendix=appendix, paragraphs=paragraphs)
        self.drafts.append(_Draft(section, refs))

    def _appendix_number(self, title: str, in_annex: bool) -> tuple[str, str]:
        """The number and title of an unnumbered head, starting the appendix when the head opens one.

        A run-in heading ends in a full stop ("A closer look."), so it never opens the appendix.
        """
        letter = APPENDIX_HEAD.fullmatch(title)
        if letter and title.endswith("."):
            letter = None
        if not self.appendix and not in_annex and self.numbered_body:
            # Appendix A is sometimes lost with its heading, so any of the first letters opens it.
            if (letter and letter["number"][0] in APPENDIX_OPENERS) or APPENDIX_TITLE.fullmatch(title):
                self._start_appendix()
        if self.appendix and letter:
            return letter["number"], letter["title"]
        return "", title


def _parent_numbers(number: str) -> list[str]:
    """"5.2.1" -> ["5", "5.2"]: the numbers of the Sections it sits under."""
    parts = number.rstrip(".").split(".")
    return [".".join(parts[:end]) for end in range(1, len(parts))]


def _div_paragraphs(div: ET.Element) -> tuple[Paragraph, ...]:
    """A div's paragraphs in order, each block formula joined to the paragraph before it."""
    paragraphs: list[Paragraph] = []
    for child in div:
        if child.tag == f"{TEI}p":
            paragraphs += _paragraphs([child])
        elif child.tag == f"{TEI}formula" and (text := _text(child)):
            formula = Sentence(text, _pages(child))
            if paragraphs:
                paragraphs[-1] = Paragraph(paragraphs[-1].sentences + (formula,))
            else:
                paragraphs.append(Paragraph((formula,)))
    return tuple(paragraphs)


def _paragraphs(elements: list[ET.Element]) -> tuple[Paragraph, ...]:
    paragraphs = []
    for p in elements:
        sentences = [Sentence(_text(s), _pages(s) or _pages(p)) for s in p.findall("tei:s", NS)]
        if not sentences:  # GROBID segments every paragraph, but a bare one is still text
            sentences = [Sentence(_text(p), _pages(p))]
        sentences = [sentence for sentence in sentences if sentence.text]
        if sentences:
            paragraphs.append(Paragraph(tuple(sentences)))
    return tuple(paragraphs)


def _place_figures(text: ET.Element, drafts: list[_Draft]) -> None:
    """Read every table and figure caption and give each to its Section, in document order."""
    for figure in text.iter(f"{TEI}figure"):
        is_table = figure.get("type") == "table"
        label = _label(figure)
        description = figure.find("tei:figDesc", NS)
        caption = _caption_paragraph(description)
        if is_table:
            grid = figure.find("tei:table", NS)
            rows = tuple(
                tuple(_text(cell) for cell in row.findall("tei:cell", NS))
                for row in (grid.findall("tei:row", NS) if grid is not None else [])
            )
            pages = set(caption.pages) | set(_pages(grid) if grid is not None else ())
            if not rows and not caption.text:
                continue
            item: Table | Caption = Table(label, caption.text, rows, tuple(sorted(pages)))
            pages_for_place = tuple(sorted(pages))
        else:
            if not caption.text:
                continue
            item = Caption(label, caption)
            pages_for_place = caption.pages
        draft = _section_of(figure, "table" if is_table else "figure", pages_for_place, drafts)
        if draft is None:
            continue
        if isinstance(item, Table):
            draft.tables.append(item)
        else:
            draft.captions.append(item)


def _label(figure: ET.Element) -> str:
    """The printed label, from the head: "Table 2 :" -> "Table 2"."""
    head = _text(figure.find("tei:head", NS))
    return re.sub(r"\s+([:.])", r"\1", head).rstrip(":. ")


def _caption_paragraph(description: ET.Element | None) -> Paragraph:
    if description is None:
        return Paragraph(())
    sentences = [Sentence(_text(s), _pages(s)) for s in description.iter(f"{TEI}s")]
    if not sentences:
        sentences = [Sentence(_text(description), _pages(description))]
    return Paragraph(tuple(sentence for sentence in sentences if sentence.text))


def _section_of(figure: ET.Element, kind: str, pages: tuple[int, ...], drafts: list[_Draft]) -> _Draft | None:
    """The Section a table or figure belongs to: the first that cites it by id, else the first that
    cites its printed number, else the last that starts on or before its first page."""
    target = f"#{figure.get(XML_ID, '')}"
    number = _text(figure.find("tei:label", NS))
    for draft in drafts:
        if any(ref_type == kind and ref_target == target for ref_type, ref_target, _ in draft.refs):
            return draft
    if number:
        for draft in drafts:
            if any(ref_type == kind and not ref_target and text == number for ref_type, ref_target, text in draft.refs):
                return draft
    if not drafts:
        return None
    if pages:
        before = [d for d in drafts if (first := d.first_page()) is not None and first <= pages[0]]
        if before:
            return before[-1]
    return drafts[0]


def _references(entries: list[ET.Element]) -> Iterator[Reference]:
    for entry in entries:
        part = entry.find("tei:analytic", NS)
        monogr = entry.find("tei:monogr", NS)
        title = _text(part.find("tei:title", NS)) if part is not None else ""
        if not title and monogr is not None:
            title = _text(monogr.find("tei:title", NS))
        authors = part.findall("tei:author", NS) if part is not None else []
        if not authors and monogr is not None:
            authors = monogr.findall("tei:author", NS)
        date = entry.find("tei:monogr/tei:imprint/tei:date[@type='published']", NS)
        when = date.get("when", "") if date is not None else ""
        identifiers = {idno.get("type", ""): _text(idno) for idno in entry.iter(f"{TEI}idno") if idno.get("type")}
        pointer = entry.find(".//tei:ptr[@target]", NS)
        if pointer is not None:
            identifiers["url"] = pointer.get("target", "")
        yield Reference(
            key=entry.get(XML_ID, ""),
            title=title,
            authors=tuple(name for author in authors if (name := _person(author))),
            year=when[:4] if when[:4].isdigit() else "",
            identifiers=identifiers,
            raw=_text(entry.find("tei:note[@type='raw_reference']", NS)),
        )


def _person(author: ET.Element) -> str:
    name = author.find("tei:persName", NS)
    if name is None:
        return ""
    parts = [_text(part) for part in name if part.tag in (f"{TEI}forename", f"{TEI}surname")]
    return " ".join(part for part in parts if part)


def _text(element: ET.Element | None) -> str:
    """The element's text with runs of whitespace collapsed to one space."""
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _pages(element: ET.Element) -> tuple[int, ...]:
    """The pages of an element's coords: boxes "page,x,y,w,h" joined by ";"."""
    boxes = (element.get("coords") or "").split(";")
    pages = {int(box.split(",")[0]) for box in boxes if box.strip()}
    return tuple(sorted(pages))
