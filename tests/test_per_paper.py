"""Per-paper retrieval on hand-built Chunks (#81): a question that names two papers gets the Chunks of each."""

from pathlib import Path

from chatbot_rag_tokenizers.parsing.chunker import Chunk
from chatbot_rag_tokenizers.retrieval.per_paper import NamedWorks, PerPaper

MANIFEST = [
    {"edition_id": "2305.07185v2", "work_id": "yu-2023-megabyte", "title": "MEGABYTE: Predicting Million-byte Sequences with Multiscale Transformers", "authors": "Lili Yu; Dániel Simig"},
    {"edition_id": "2412.09871v1", "work_id": "pagnoni-2024-blt", "title": "Byte Latent Transformer: Patches Scale Better Than Tokens", "authors": "Artidoro Pagnoni; Ram Pasunuru"},
    {"edition_id": "2404.14408v1", "work_id": "slagle-2024-spacebyte", "title": "SpaceByte: Towards Deleting Tokenization from Large Language Modeling", "authors": "Kevin Slagle"},
]
QUESTION = "How do MEGABYTE and the Byte Latent Transformer differ in the way they group bytes into patches?"


def chunk(chunk_id: str, edition_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        edition_id=edition_id,
        pinned_id=edition_id,
        version="",
        file_sha256=edition_id,
        section_number="",
        section_title="",
        section_path=("1 Introduction",),
        appendix=False,
        kind="text",
        page_start=None,
        page_end=None,
        header="",
        text=chunk_id,
        token_count=1,
    )


class Ranked:
    """A retriever that ranks the Chunks in the order it was given them, whatever the query."""

    def __init__(self, *chunk_ids: str) -> None:
        self.chunk_ids = chunk_ids
        self.queries: list[tuple[str, int]] = []

    device, parameters, dimension = "cpu", None, None

    def query(self, text: str, k: int) -> list[tuple[str, float]]:
        self.queries.append((text, k))
        return [(chunk_id, 1.0 - rank / 100) for rank, chunk_id in enumerate(self.chunk_ids[:k])]

    def save(self, directory: Path) -> None: ...


# SpaceByte restates both papers, so the question as one ranking finds it first and BLT last.
CHUNKS = [
    chunk("spacebyte-1", "2404.14408v1"),
    chunk("spacebyte-2", "2404.14408v1"),
    chunk("megabyte-1", "2305.07185v2"),
    chunk("spacebyte-3", "2404.14408v1"),
    chunk("megabyte-2", "2305.07185v2"),
    chunk("blt-1", "2412.09871v1"),
    chunk("blt-2", "2412.09871v1"),
]


def per_paper(names: dict[str, list[str]], chunks: list[Chunk] = CHUNKS, manifest: list[dict[str, str]] = MANIFEST) -> PerPaper:
    by_id = {c.chunk_id: c for c in chunks}
    return PerPaper(Ranked(*by_id), by_id, NamedWorks(by_id, manifest), lambda text: names.get(text, []))


def ids(ranking: list[tuple[str, float]]) -> list[str]:
    return [chunk_id for chunk_id, _ in ranking]


def test_a_question_naming_two_papers_fills_the_slots_from_each_papers_best_chunks_in_rotation():
    retriever = per_paper({QUESTION: ["MEGABYTE", "Byte Latent Transformer"]})

    assert ids(retriever.query(QUESTION, 3)) == ["megabyte-1", "blt-1", "megabyte-2"]


def test_a_question_naming_one_paper_or_none_is_ranked_as_asked():
    for names in ([], ["MEGABYTE"]):
        assert ids(per_paper({QUESTION: names}).query(QUESTION, 3)) == ["spacebyte-1", "spacebyte-2", "megabyte-1"]


def test_a_name_no_work_matches_is_dropped_and_two_names_of_the_same_works_count_once():
    as_asked = ["spacebyte-1", "spacebyte-2", "megabyte-1"]
    for names in (["MEGABYTE", "Rényi efficiency"], ["MEGABYTE", "MEGABYTE's multiscale Transformers"]):
        assert ids(per_paper({QUESTION: names}).query(QUESTION, 3)) == as_asked


def test_a_name_with_et_al_finds_the_works_whose_first_author_has_that_surname():
    retriever = per_paper({})

    assert retriever.works("Yu et al.'s byte model") == {"yu-2023-megabyte"}
    assert retriever.works("Pagnoni et al") == {"pagnoni-2024-blt"}
    assert retriever.works("Simig et al.") == set()  # the second author, not the first


def test_a_name_whose_words_are_in_two_works_titles_takes_both_in_one_stream():
    fast = {"edition_id": "2601.00001v1", "work_id": "fast-blt", "title": "Fast Byte Latent Transformer", "authors": "A. Author"}
    retriever = per_paper({QUESTION: ["MEGABYTE", "Byte Latent Transformer"]}, [*CHUNKS, chunk("fast-blt-1", "2601.00001v1")], [*MANIFEST, fast])

    assert retriever.works("Byte Latent Transformer") == {"pagnoni-2024-blt", "fast-blt"}
    assert retriever.works("Bytes Latent Transformer") == set()  # whole words only
    assert ids(retriever.query(QUESTION, 5)) == ["megabyte-1", "blt-1", "megabyte-2", "blt-2", "fast-blt-1"]


def test_once_the_named_papers_run_out_the_rest_of_the_ranking_fills_the_slots():
    retriever = per_paper({QUESTION: ["MEGABYTE", "Byte Latent Transformer"]})

    assert ids(retriever.query(QUESTION, 7))[4:] == ["spacebyte-1", "spacebyte-2", "spacebyte-3"]


def test_an_edition_without_a_manifest_row_is_its_own_work_with_no_title():
    orphan = chunk("orphan-1", "2601.99999v1")
    retriever = per_paper({QUESTION: ["MEGABYTE", "Byte Latent Transformer"]}, [*CHUNKS, orphan])

    assert ids(retriever.query(QUESTION, 8))[-1] == "orphan-1"
