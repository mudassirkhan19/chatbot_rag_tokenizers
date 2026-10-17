"""The TEI reader: turns GROBID's TEI into a structured document of Sections, paragraphs and sentences.

It reads only content that is the same on every parse of a file (ADR 0024): the title, the abstract,
and each body Section's head, sentences and the pages they sit on. GROBID's request timestamp, funders
and figure graphics change between parses and are never read.

GROBID gives Sections as a flat list of ``div``s, so each Section's path is rebuilt from its number:
3.1 sits under 3 when the paper has a Section 3, and directly under the title when GROBID lost that
heading. An unnumbered head (often a run-in paragraph heading) sits under the last numbered Section.
"""

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
ABSTRACT = "Abstract"


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
class Section:
    number: str  # as printed, e.g. "3.1"; "" when the head has none
    title: str
    path: tuple[str, ...]  # headings from the top-level Section down to this one, e.g. ("3 Method", "3.1 Data")
    appendix: bool
    paragraphs: tuple[Paragraph, ...]


@dataclass(frozen=True)
class Document:
    title: str
    grobid_version: str  # as the TEI header reports it, e.g. "0.9.1"
    sections: tuple[Section, ...]  # the abstract first, then the body in reading order


def read_tei(tei: str) -> Document:
    root = ET.fromstring(tei)
    header = root.find("tei:teiHeader", NS)
    if header is None:
        raise ValueError("the TEI has no teiHeader")
    application = header.find(".//tei:appInfo/tei:application[@ident='GROBID']", NS)
    sections = list(_abstract(header))
    sections += _body_sections(root.find("tei:text/tei:body", NS))
    return Document(
        title=_text(header.find("tei:fileDesc/tei:titleStmt/tei:title[@type='main']", NS)),
        grobid_version=application.get("version", "") if application is not None else "",
        sections=tuple(sections),
    )


def _abstract(header: ET.Element) -> Iterator[Section]:
    paragraphs = _paragraphs(header.findall("tei:profileDesc/tei:abstract//tei:p", NS))
    if paragraphs:
        yield Section(number="", title=ABSTRACT, path=(ABSTRACT,), appendix=False, paragraphs=paragraphs)


def _body_sections(body: ET.Element | None) -> list[Section]:
    if body is None:
        return []
    sections: list[Section] = []
    headings: dict[str, str] = {}  # Section number -> its heading, for the paths of the Sections under it
    last_numbered: tuple[str, ...] = ()  # path of the last numbered Section
    for div in body.findall("tei:div", NS):
        paragraphs = _paragraphs(div.findall("tei:p", NS))
        head = div.find("tei:head", NS)
        if head is None:
            # A div without a head continues the Section before it.
            if sections:
                previous = sections.pop()
                sections.append(_with_paragraphs(previous, previous.paragraphs + paragraphs))
            elif paragraphs:
                sections.append(Section(number="", title="", path=(), appendix=False, paragraphs=paragraphs))
            continue
        number = (head.get("n") or "").strip()
        title = _text(head)
        if number:
            heading = f"{number} {title}"
            parents = _parent_numbers(number)
            path = tuple(headings[parent] for parent in parents if parent in headings) + (heading,)
            headings[number.rstrip(".")] = heading
            last_numbered = path
        else:
            path = last_numbered + (title,)
        sections.append(Section(number=number, title=title, path=path, appendix=False, paragraphs=paragraphs))
    return sections


def _parent_numbers(number: str) -> list[str]:
    """"5.2.1" -> ["5", "5.2"]: the numbers of the Sections it sits under."""
    parts = number.rstrip(".").split(".")
    return [".".join(parts[:end]) for end in range(1, len(parts))]


def _with_paragraphs(section: Section, paragraphs: tuple[Paragraph, ...]) -> Section:
    return Section(section.number, section.title, section.path, section.appendix, paragraphs)


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


def _text(element: ET.Element | None) -> str:
    """The element's text with runs of whitespace collapsed to one space."""
    return " ".join("".join(element.itertext()).split()) if element is not None else ""


def _pages(element: ET.Element) -> tuple[int, ...]:
    """The pages of an element's coords: boxes "page,x,y,w,h" joined by ";"."""
    boxes = (element.get("coords") or "").split(";")
    pages = {int(box.split(",")[0]) for box in boxes if box.strip()}
    return tuple(sorted(pages))
