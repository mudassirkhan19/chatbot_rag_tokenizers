"""The Chunker: turns a structured document into Chunks under the chunking config (ADR 0025).

A pure function of the document, the file it came from and the config, so Chunks can be rebuilt
from cached TEI without the parser. Within each Section, whole paragraphs are packed in order up to
the token budget. A paragraph over the budget is split at its sentences, and a sentence over the
budget at its words, so no Chunk is over the budget. A Chunk never crosses a Section, and Chunks
never overlap.

Each Section's text Chunks come first, then its tables, then its figure captions (ADR 0026). A table
is one Chunk of kind "table": its label, Section heading and caption on the first line, then one line
per row with cells joined by " | ". A table over the budget is cut between rows (a row over the budget
between words), and each part repeats the first line, unless that line alone would take more than half
the budget. A figure caption is one Chunk of kind "caption", packed like a paragraph.
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .tei import Caption, Document, Paragraph, Section, Sentence, Table

HEADER_SEPARATOR = " › "
PARAGRAPH_BREAK = "\n\n"
ROW_BREAK = "\n"
CELL_SEPARATOR = " | "


@dataclass(frozen=True)
class ParsedFile:
    """The file a document was parsed from, and how Chunks cite it."""

    pinned_id: str  # the Edition id pinned to a Version, e.g. "2112.06598v2" (ADR 0015)
    version: str  # the arXiv Version, e.g. "v2"; "" for a venue Edition
    sha256: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str  # the file hash's first 16 hex digits and the Chunk's place in the file
    pinned_id: str
    version: str
    file_sha256: str
    section_number: str
    section_title: str
    section_path: tuple[str, ...]
    appendix: bool
    kind: str  # "text", "table" or "caption"
    page_start: int | None  # the citation anchor's page range; None when GROBID gave no coordinates
    page_end: int | None
    header: str  # "title › Section path", kept out of the text so citations quote clean text
    text: str
    token_count: int


@dataclass(frozen=True)
class _Piece:
    """A run of text that is never split further: a paragraph, a sentence or a run of words."""

    text: str
    pages: tuple[int, ...]
    starts_paragraph: bool


def chunk_document(document: Document, file: ParsedFile, token_budget: int, count_tokens: Callable[[str], int]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for section in document.sections:
        texts: list[tuple[str, str, set[int]]] = [
            ("text", text, pages)
            for text, pages in _pack(_pieces(section.paragraphs, token_budget, count_tokens), token_budget, count_tokens)
        ]
        for table in section.tables:
            texts += [("table", text, set(table.pages)) for text in _table_texts(table, section, token_budget, count_tokens)]
        for caption in section.captions:
            paragraph = _labelled(caption)
            texts += [("caption", text, pages) for text, pages in _pack(_pieces((paragraph,), token_budget, count_tokens), token_budget, count_tokens)]
        for kind, text, pages in texts:
            chunks.append(
                Chunk(
                    chunk_id=f"{file.sha256[:16]}-{len(chunks):04d}",
                    pinned_id=file.pinned_id,
                    version=file.version,
                    file_sha256=file.sha256,
                    section_number=section.number,
                    section_title=section.title,
                    section_path=section.path,
                    appendix=section.appendix,
                    kind=kind,
                    page_start=min(pages) if pages else None,
                    page_end=max(pages) if pages else None,
                    header=HEADER_SEPARATOR.join((document.title, *section.path)),
                    text=text,
                    token_count=count_tokens(text),
                )
            )
    return chunks


def _table_texts(table: Table, section: Section, token_budget: int, count_tokens: Callable[[str], int]) -> list[str]:
    """A table, linearised: its first line names it, its Section and its caption; then a line per row."""
    name = table.label or "Table"
    if section.path:
        name += f" ({section.path[-1]})"
    first = f"{name}: {table.caption}" if table.caption else name
    rows = [CELL_SEPARATOR.join(row).rstrip() for row in table.rows]
    whole = ROW_BREAK.join([first, *rows])
    if count_tokens(whole) <= token_budget:
        return [whole]
    repeat = count_tokens(first) <= token_budget // 2
    lead = [first] if repeat else []
    room = token_budget - count_tokens(first) if repeat else token_budget
    units = []
    for line in rows if repeat else [first, *rows]:
        units += [line] if count_tokens(line) <= room else _word_runs(line, room, count_tokens)
    texts: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and count_tokens(ROW_BREAK.join([*lead, *current, unit])) > token_budget:
            texts.append(ROW_BREAK.join([*lead, *current]))
            current = []
        current.append(unit)
    if current:
        texts.append(ROW_BREAK.join([*lead, *current]))
    return texts


def _labelled(caption: Caption) -> Paragraph:
    """The caption with its label in front, unless GROBID already kept the label in the text."""
    sentences = caption.paragraph.sentences
    squashed = caption.paragraph.text.replace(" ", "").lower()
    if not caption.label or squashed.startswith(caption.label.replace(" ", "").lower()):
        return caption.paragraph
    first = sentences[0]
    return Paragraph((Sentence(f"{caption.label}: {first.text}", first.pages), *sentences[1:]))


def _pieces(paragraphs: tuple[Paragraph, ...], token_budget: int, count_tokens: Callable[[str], int]) -> Iterator[_Piece]:
    for paragraph in paragraphs:
        if count_tokens(paragraph.text) <= token_budget:
            yield _Piece(paragraph.text, paragraph.pages, starts_paragraph=True)
            continue
        first = True
        for sentence in paragraph.sentences:
            if count_tokens(sentence.text) <= token_budget:
                runs = [sentence.text]
            else:
                runs = _word_runs(sentence.text, token_budget, count_tokens)
            for run in runs:
                yield _Piece(run, sentence.pages, starts_paragraph=first)
                first = False


def _word_runs(text: str, token_budget: int, count_tokens: Callable[[str], int]) -> list[str]:
    """A sentence over the budget, cut between words into runs within it (a last resort: GROBID's
    sentence splitter misses some boundaries, and tables it missed come out as one long "sentence")."""
    runs: list[str] = []
    current: list[str] = []
    for word in text.split(" "):
        if current and count_tokens(" ".join([*current, word])) > token_budget:
            runs.append(" ".join(current))
            current = []
        current.append(word)
    runs.append(" ".join(current))
    return runs


def _pack(pieces: Iterator[_Piece], token_budget: int, count_tokens: Callable[[str], int]) -> Iterator[tuple[str, set[int]]]:
    """Greedily join pieces, in order, into texts within the budget, with the pages each text covers."""
    text = ""
    pages: set[int] = set()
    for piece in pieces:
        if text:
            joined = text + (PARAGRAPH_BREAK if piece.starts_paragraph else " ") + piece.text
            if count_tokens(joined) <= token_budget:
                text = joined
                pages.update(piece.pages)
                continue
            yield text, pages
        text, pages = piece.text, set(piece.pages)
    if text:
        yield text, pages
