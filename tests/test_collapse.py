"""The Collapsed ranking on hand-built Chunks (#80, ADR 0072): copies of a passage are matched by their text, wherever
their files put them in the Section."""

from pathlib import Path

from chatbot_rag_tokenizers.parsing.chunker import Chunk
from chatbot_rag_tokenizers.retrieval.collapse import Collapsed, Merged

# CANINE's NER result, as its TACL Edition words it, and as its arXiv v4 words it after a revision.
NER = (
    "On the MasakhaNER data set CANINE-C achieves an average F1 of 50.0 across the ten African languages, while mBERT "
    "achieves 59.5, a gap that narrows on languages written in scripts that mBERT's vocabulary covers poorly, such as "
    "Amharic, where CANINE-C outperforms mBERT by a wide margin."
)
NER_REWORDED = (
    "On the MasakhaNER data set CANINE-C achieves an average F1 of 50.0 across the ten African languages, whereas mBERT "
    "achieves 59.5, a gap that narrows on languages written in scripts that mBERT's vocabulary covers poorly, such as "
    "Amharic, where CANINE-C beats mBERT by a wide margin."
)
HASHING = (
    "CANINE embeds each character with several hash functions into a small number of buckets, and concatenates the "
    "embeddings of the buckets, so that it needs no fixed vocabulary of characters and no table of a million rows."
)

MANIFEST = [
    {"edition_id": "2022.tacl-1.5", "work_id": "clark-2022-canine", "canonical": "yes", "survey": ""},
    {"edition_id": "2103.06874v4", "work_id": "clark-2022-canine", "canonical": "", "survey": ""},
    {"edition_id": "2105.13626v3", "work_id": "xue-2022-byt5", "canonical": "", "survey": ""},
]


def chunk(chunk_id: str, edition_id: str, file: str, section: tuple[str, ...], text: str, pinned_id: str = "") -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        edition_id=edition_id,
        pinned_id=pinned_id or edition_id,
        version="",
        file_sha256=file,
        section_number="",
        section_title=section[-1],
        section_path=section,
        appendix=False,
        kind="text",
        page_start=None,
        page_end=None,
        header="",
        text=text,
        token_count=len(text.split()),
    )


class Ranked:
    """A retriever that ranks the Chunks in the order it was given them."""

    def __init__(self, *chunk_ids: str) -> None:
        self.chunk_ids = chunk_ids

    device, parameters, dimension = "cpu", None, None

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        return [(chunk_id, 1.0 - rank / 100) for rank, chunk_id in enumerate(self.chunk_ids[:k])]

    def save(self, directory: Path) -> None: ...


def collapse(*chunks: Chunk, k: int = 5):
    by_id = {c.chunk_id: c for c in chunks}
    return Collapsed(Ranked(*by_id), by_id, MANIFEST, pool=50, overlap=0.5).collapse("CANINE on Amharic", k)


def test_a_reworded_copy_in_another_section_path_of_another_file_is_merged():
    # GROBID nested the Section in the arXiv Version only, and the revision reworded two words.
    arxiv = chunk("arxiv-0043", "2103.06874v4", "arxiv", ("4 Experiments", "4.4 NER Results"), NER_REWORDED)
    tacl = chunk("tacl-0048", "2022.tacl-1.5", "tacl", ("4.4 NER Results",), NER)

    result = collapse(arxiv, tacl)

    # One slot, at the arXiv copy's rank, shown by the Canonical Edition's copy.
    assert [chunk_id for chunk_id, _ in result.ranking] == ["tacl-0048"]
    assert result.merged["tacl-0048"] == Merged("clark-2022-canine", ("2103.06874v4",), ("arxiv-0043",), survey=False)


def test_a_renumbered_v1_joins_the_same_slot_and_the_work_s_other_passage_keeps_its_own():
    v1 = chunk("v1-0040", "2103.06874v4", "v1", ("5 Experiments", "5.3 NER Results"), NER, pinned_id="2103.06874v1")
    hashing = chunk("tacl-0010", "2022.tacl-1.5", "tacl", ("2 Method",), HASHING)
    tacl = chunk("tacl-0048", "2022.tacl-1.5", "tacl", ("4.4 NER Results",), NER)
    arxiv = chunk("arxiv-0043", "2103.06874v4", "arxiv", ("4 Experiments", "4.4 NER Results"), NER_REWORDED)

    result = collapse(v1, hashing, tacl, arxiv)

    assert [chunk_id for chunk_id, _ in result.ranking] == ["tacl-0048", "tacl-0010"]
    assert result.merged["tacl-0048"].copies == ("v1-0040", "arxiv-0043")
    assert result.merged["tacl-0048"].editions == ("2103.06874v1", "2103.06874v4")
    assert result.merged["tacl-0010"].copies == ()
    assert result.distinct == 2


def test_the_same_text_in_another_work_keeps_its_slot():
    # ByT5 quoting CANINE's result word for word is another paper's Chunk, not a copy.
    canine = chunk("tacl-0048", "2022.tacl-1.5", "tacl", ("4.4 NER Results",), NER)
    byt5 = chunk("byt5-0030", "2105.13626v3", "byt5", ("6 Related Work",), NER)

    result = collapse(canine, byt5)

    assert [chunk_id for chunk_id, _ in result.ranking] == ["tacl-0048", "byt5-0030"]


def test_two_chunks_of_one_file_are_never_merged():
    # A table repeated in an appendix of the same file is two places of one file.
    body = chunk("tacl-0048", "2022.tacl-1.5", "tacl", ("4.4 NER Results",), NER)
    appendix = chunk("tacl-0090", "2022.tacl-1.5", "tacl", ("A Full Results",), NER)
    arxiv = chunk("arxiv-0043", "2103.06874v4", "arxiv", ("4 Experiments", "4.4 NER Results"), NER_REWORDED)

    result = collapse(body, appendix, arxiv)

    # The arXiv copy joins the best-ranked slot it is a copy of, and the appendix keeps its own.
    assert [chunk_id for chunk_id, _ in result.ranking] == ["tacl-0048", "tacl-0090"]
    assert result.merged["tacl-0048"].copies == ("arxiv-0043",)


# A table cut into two Chunks, each repeating its caption, as two Versions of one paper both cut it.
CAPTION = "Table 2 (3.6 Matched-compression sweep): BPC normalises the log-likelihood by the length of the text, not by its tokens."
FIRST_ROWS = CAPTION + " | V | TPC | BPC | 300 | 0.5430 | 3.8903 | 400 | 0.5012 | 3.8571 |"
LAST_ROWS = CAPTION + " | 600 | 0.4430 | 3.7739 | 800 | 0.4170 | 3.7295 | 1200 | 0.3831 | 3.6621 |"


def test_a_chunk_sharing_only_a_caption_with_another_file_s_chunk_is_no_copy_when_its_own_copy_is_in_that_file():
    first_v1 = chunk("v1-0024", "2103.06874v4", "v1", ("3.6 Matched-compression sweep",), FIRST_ROWS, pinned_id="2103.06874v1")
    last_v4 = chunk("v4-0025", "2103.06874v4", "v4", ("3.6 Matched-compression sweep",), LAST_ROWS)
    # Not retrieved, but in the corpus: v1's own copy of the last rows, and v4's of the first.
    last_v1 = chunk("v1-0025", "2103.06874v4", "v1", ("3.6 Matched-compression sweep",), LAST_ROWS, pinned_id="2103.06874v1")
    first_v4 = chunk("v4-0024", "2103.06874v4", "v4", ("3.6 Matched-compression sweep",), FIRST_ROWS)
    chunks = {c.chunk_id: c for c in (first_v1, last_v4, last_v1, first_v4)}

    result = Collapsed(Ranked("v1-0024", "v4-0025"), chunks, MANIFEST, pool=50, overlap=0.5).collapse("BPC at 1200", 5)

    # Each holds rows the other doesn't: two slots.
    assert [chunk_id for chunk_id, _ in result.ranking] == ["v1-0024", "v4-0025"]
