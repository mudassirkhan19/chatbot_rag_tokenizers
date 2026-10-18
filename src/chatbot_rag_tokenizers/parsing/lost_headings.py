"""Numbered headings GROBID left inside a paragraph (#41, ADR 0041).

GROBID sometimes doesn't recognise a heading and leaves it in a paragraph: at the start
(``<s>2 Related Work Our work ...``), as a paragraph of its own, or at the end of a sentence
(``... a finding of 4 Analysis</s>``). The text survives, but the Section before it would take every
paragraph of the lost one. A paragraph is split at a lost heading when all of these hold:

- its first sentence starts with a Section number and a capital ("2 Related Work", not "3 models were"),
  or a sentence ends with one;
- those words sit on boxes in one type, taller than the body lines of both the document and the div
  (a div's lines can be smaller), as a heading's larger type is, and taller than the paragraph's other lines;
- the number continues the Sections before it: after 1 comes 1.1, 2 or 2.1, never 1 again or 4;
- the document's real headings of the same height say how wide that type prints, and the words fill the
  tall boxes' width to within 10%.

TEI gives no boundary between a heading at the start and the text after it, so there the width decides
where the heading ends. Each character is weighted by its rough printed width, as a capital is wider than
an "i". The heading never ends in a word that typically opens a sentence ("In", "We", "The") or in a bare
number: such a word is the start of the text, which the width estimate can take by one short word. Nor
does it hold a Section number, which starts the next lost heading. At the end of a sentence the Section
number marks where the heading starts, and the width only confirms it.
"""

import copy
import re
import statistics
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass

TEI = "{http://www.tei-c.org/ns/1.0}"
HEADING_START = re.compile(r"\s*(?P<number>\d+(?:\.\d+)*) +[A-Z]")
NUMBER = re.compile(r"\d+(?:\.\d+)*\.?")
SUBSECTION = re.compile(r"\d+(?:\.\d+)+\.?")
TALLER = 1.1  # a heading's boxes are at least this much taller than the body lines
SAME_TYPE = 0.3  # points: real headings this close in height are printed in the same type
WIDTH_TOLERANCE = 0.1
MOST_WORDS = 25
SENTENCE_OPENERS = frozenset(
    "a an and as at by each for from given here if in is it many most of on one our since so that the these "
    "there this to we when while with".split()
)
# Rough advance widths of a serif font, relative to a lowercase "n"; other characters count as 0.7.
GLYPH_WIDTHS = {
    **dict.fromkeys("abcdeghknopqsuvxyz0123456789", 1.0),
    **dict.fromkeys("fijlrt", 0.6),
    **dict.fromkeys("mw", 1.5),
    **dict.fromkeys("ABCDEFGHKNOPQRSUVXYZ", 1.4),
    **dict.fromkeys("IJ", 0.76),
    **dict.fromkeys("LT", 1.24),
    **dict.fromkeys("MW", 1.84),
}


@dataclass(frozen=True)
class _Box:
    raw: str  # "page,x,y,width,height" as GROBID wrote it
    width: float
    height: float


class Typography:
    """How the document prints its body lines and headings: the lines' height, and the headings' glyph widths
    per point of box by the boxes' height."""

    def __init__(self, divs: list[ET.Element]) -> None:
        lines = [box.height for div in divs for p in div.iter(f"{TEI}p") for box in _boxes(p)]
        self.body_line = statistics.median(lines) if lines else 0.0
        heads = [head for div in divs if (head := div.find(f"{TEI}head")) is not None]
        self._heads: list[tuple[float, float, float]] = []  # (height, total box width, glyph width of the text)
        for head in heads:
            number, boxes = (head.get("n") or "").strip(), _boxes(head)
            if NUMBER.fullmatch(number) and boxes:
                text = f"{number} {' '.join(''.join(head.itertext()).split())}"
                height = statistics.median(box.height for box in boxes)
                self._heads.append((height, sum(box.width for box in boxes), _glyph_width(text)))

    def per_point(self, height: float) -> float | None:
        """Glyph width per point of box for headings of this height; None when the document has none."""
        same = [(width, glyphs) for h, width, glyphs in self._heads if abs(h - height) < SAME_TYPE]
        points = sum(width for width, _ in same)
        return sum(glyphs for _, glyphs in same) / points if points else None


def split_lost_headings(div: ET.Element, last_number: str, typography: Typography) -> list[ET.Element]:
    """The div as one or more divs, a new one starting at each lost heading with that heading as its head.

    ``last_number`` is the number of the last numbered Section before the div ("" when there is none).
    """
    head = div.find(f"{TEI}head")
    if head is not None and NUMBER.fullmatch(number := (head.get("n") or "").strip()):
        last_number = number.rstrip(".")
    lines = [box.height for p in div.iter(f"{TEI}p") for box in _boxes(p)]
    finder = _Finder(max(typography.body_line, statistics.median(lines) if lines else 0.0), typography)
    parts = [ET.Element(div.tag, div.attrib)]
    for child in div:
        rest: ET.Element | None = child
        while rest is not None and rest.tag == f"{TEI}p" and (found := finder.find(rest, last_number)):
            before, heading, rest = found
            if before is not None:
                parts[-1].append(before)
            parts.append(ET.Element(div.tag, div.attrib))
            parts[-1].append(heading)
            last_number = heading.get("n", "")
        if rest is not None:
            parts[-1].append(rest)
    return parts if len(parts) > 1 else [div]


@dataclass(frozen=True)
class _Finder:
    body: float  # height of the body lines, in points
    typography: Typography

    def find(self, p: ET.Element, last_number: str) -> tuple[ET.Element | None, ET.Element, ET.Element | None] | None:
        """The paragraph's first lost heading, with the paragraph before and after it (None when no text is left)."""
        sentences = p.findall(f"{TEI}s")
        for index, sentence in enumerate(sentences):
            if index == 0 and (found := self._at_start(sentence, last_number)) and _stands_out(p, found[0]):
                heading, count = found
                rest = _cut(sentence, heading, lambda text: _without_first_words(text, count), first=True)
                return None, heading, _paragraph(p, [rest, *sentences[1:]], heading)
            if (found := self._at_end(sentence, last_number)) and _stands_out(p, found[0]):
                heading, count = found
                rest = _cut(sentence, heading, lambda text: _without_last_words(text, count), first=False)
                return _paragraph(p, [*sentences[:index], rest], heading), heading, _paragraph(p, sentences[index + 1 :], heading)
        return None

    def _at_start(self, sentence: ET.Element, last_number: str) -> tuple[ET.Element, int] | None:
        """The heading that opens the sentence, and its number of words: as many first words as fill its first tall boxes."""
        leading = sentence.text or ""  # only the text before the sentence's first element can be the heading
        match = HEADING_START.match(leading)
        if not match or not _follows(match["number"], last_number):
            return None
        tall = self._tall(_boxes(sentence))
        target = self._target(tall)
        words = leading.split()
        # A heading holds no Section number: "4.4 Experts 4.4.1 Architecture" is two headings.
        end = next((i for i, word in enumerate(words[1:MOST_WORDS], 1) if SUBSECTION.fullmatch(word)), min(len(words), MOST_WORDS))
        if target is None or end < 2:
            return None
        count = min(range(2, end + 1), key=lambda k: abs(_glyph_width(" ".join(words[:k])) - target))
        if not _fits(" ".join(words[:count]), target):
            return None
        while count > 2 and (words[count - 1].lower() in SENTENCE_OPENERS or words[count - 1].isdigit()):
            count -= 1
        return _head(match["number"], words[1:count], tall), count

    def _at_end(self, sentence: ET.Element, last_number: str) -> tuple[ET.Element, int] | None:
        """The heading that closes the sentence, and its number of words: the last words from a Section number on,
        when they fill its last tall boxes."""
        children = list(sentence)
        words = ((children[-1].tail if children else sentence.text) or "").split()
        tall = self._tall(_boxes(sentence)[::-1])[::-1]
        target = self._target(tall)
        if target is None:
            return None
        for start in range(max(len(words) - MOST_WORDS, 0), len(words) - 1):
            match = HEADING_START.match(" ".join(words[start:]))
            if (
                match
                and match["number"] == words[start]
                and not any(SUBSECTION.fullmatch(word) for word in words[start + 1 :])
                and _follows(match["number"], last_number)
                and _fits(" ".join(words[start:]), target)
            ):
                return _head(match["number"], words[start + 1 :], tall), len(words) - start
        return None

    def _tall(self, boxes: list[_Box]) -> list[_Box]:
        """The boxes up to the first one no taller than a body line, or not in the first one's type."""
        tall: list[_Box] = []
        for box in boxes:
            if box.height <= self.body * TALLER or (tall and abs(box.height - tall[0].height) >= SAME_TYPE):
                break
            tall.append(box)
        return tall

    def _target(self, tall: list[_Box]) -> float | None:
        """The glyph width of a heading printed in these boxes; None when the document has no heading that tall."""
        per_point = self.typography.per_point(statistics.median(box.height for box in tall)) if tall else None
        return sum(box.width for box in tall) * per_point if per_point else None


def _stands_out(p: ET.Element, heading: ET.Element) -> bool:
    """Whether the heading is taller than the rest of its paragraph's lines, if it has any."""
    rest = [box.height for box in _boxes(p) if box.raw not in set((heading.get("coords") or "").split(";"))]
    return not rest or statistics.median(rest) * TALLER < statistics.median(box.height for box in _boxes(heading))


def _fits(text: str, target: float) -> bool:
    return abs(_glyph_width(text) - target) <= WIDTH_TOLERANCE * target


def _head(number: str, title: list[str], boxes: list[_Box]) -> ET.Element:
    head = ET.Element(f"{TEI}head", {"n": number, "coords": ";".join(box.raw for box in boxes)})
    head.text = " ".join(title)
    return head


def _cut(sentence: ET.Element, heading: ET.Element, keep: Callable[[str], str], first: bool) -> ET.Element:
    """A copy of the sentence without the heading: ``keep`` cuts the text it starts or ends with."""
    rest = copy.deepcopy(sentence)
    children = list(rest)
    if first or not children:
        rest.text = keep(rest.text or "")
    else:
        children[-1].tail = keep(children[-1].tail or "")
    return rest


def _paragraph(p: ET.Element, sentences: list[ET.Element], heading: ET.Element) -> ET.Element | None:
    """A paragraph like p holding these sentences, without the heading's boxes; None when they hold no text."""
    rest = ET.Element(p.tag, p.attrib)
    rest.extend(sentence for sentence in sentences if "".join(sentence.itertext()).strip())
    boxes = set((heading.get("coords") or "").split(";"))
    for element in (rest, *rest):
        if coords := element.get("coords"):
            element.set("coords", ";".join(box for box in coords.split(";") if box.strip() and box not in boxes))
    return rest if len(rest) else None


def _without_first_words(text: str, count: int) -> str:
    match = re.match(r"\s*" + r"\S+\s+" * (count - 1) + r"\S+\s*", text)
    assert match is not None
    return text[match.end() :]


def _without_last_words(text: str, count: int) -> str:
    match = re.search(r"\S+" + r"\s+\S+" * (count - 1) + r"\s*$", text)
    assert match is not None
    return text[: match.start()]


def _follows(number: str, last_number: str) -> bool:
    """Whether a Section numbered so can come soon after the last numbered one.

    It counts on by one or two at some level of the last number (one Section may be lost unseen) and starts
    any level below that at 1: after 2.1 come 2.1.1, 2.2, 2.3, 3, 3.1 or 4, never 2.1 again, 1.5 or 2.10.
    """
    if last_number and not NUMBER.fullmatch(last_number):  # a body Section GROBID numbered "A.1"
        return False
    parts = [int(part) for part in number.split(".")]
    last = [int(part) for part in last_number.split(".")] if last_number else [0]
    if 0 in parts:  # Sections are numbered from 1: "0.2" is a value
        return False
    level = next((i for i, (a, b) in enumerate(zip(parts, last, strict=False)) if a != b), min(len(parts), len(last)))
    if level == len(parts):  # the same number, or one of the Sections above the last
        return False
    step = parts[level] - (last[level] if level < len(last) else 0)
    return 1 <= step <= 2 and all(part == 1 for part in parts[level + 1 :])


def _boxes(element: ET.Element) -> list[_Box]:
    boxes = []
    for raw in (element.get("coords") or "").split(";"):
        fields = raw.split(",")
        if len(fields) == 5:
            boxes.append(_Box(raw, float(fields[3]), float(fields[4])))
    return boxes


def _glyph_width(text: str) -> float:
    return sum(GLYPH_WIDTHS.get(character, 0.7) for character in text if not character.isspace())
