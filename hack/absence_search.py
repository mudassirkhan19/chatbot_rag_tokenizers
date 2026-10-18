"""Search every Chunk for each unanswerable question (ADR 0045): `uv run python hack/absence_search.py`.

An unanswerable question is only unanswerable if no Chunk answers it. For each one in data/eval/evaluation-set.jsonl
this runs the question, and a few probe queries worded closer to how an answer would read, through both BM25 and the
dense baseline, and writes the top 10 of each to data/eval/absence-evidence.md for the developer to read through.
Needs `just index` to have built both retrievers.
"""

from dataclasses import dataclass
from pathlib import Path

from chatbot_rag_tokenizers.evaluation.evalset import load_evaluation_set
from chatbot_rag_tokenizers.parsing.config import load_parse_config
import chatbot_rag_tokenizers.retrieval.index as index
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus

EVALUATION_SET = Path("data/eval/evaluation-set.jsonl")
EVIDENCE = Path("data/eval/absence-evidence.md")
DEPTH = 10
SNIPPET = 160  # characters of each Chunk's text shown


@dataclass(frozen=True)
class Search:
    probes: tuple[str, ...]  # worded the way a sentence holding the answer would be, so a miss isn't just the question's wording
    reading: str  # what the drafter read in the results: the nearest miss, and why it doesn't answer the question


SEARCHES = {
    "bpe-english-french": Search(
        ("Sennrich BPE subword units English French BLEU", "English→French translation results subword units newstest"),
        "The paper's own results are English→German and English→Russian only. Other papers' English–French BLEU is"
        " for their own systems, not Sennrich et al.'s.",
    ),
    "blt-70b-mmlu": Search(
        ("Byte Latent Transformer 70B MMLU", "BLT byte-level model 70B parameters results"),
        "The Byte Latent Transformer is trained up to 8B parameters; no Chunk gives a 70B BLT.",
    ),
    "llama-3-shan-premium": Search(
        ("Llama 3 tokenizer Shan tokenization parity", "Shan language token premium Llama 3"),
        "Petrov et al. predate Llama 3 and measure GPT-2, RoBERTa, ChatGPT, GPT-4 and others. A 2026 paper quotes"
        " their cl100k_base figure for Shan, not a Llama 3 one.",
    ),
    "fast-wordpiece-gpu": Search(
        ("Fast WordPiece GPU throughput", "LinMaxMatch WordPiece tokenization on GPU"),
        "Fast WordPiece reports CPU timings only. The GPU tokenizers that come up are other systems.",
    ),
    "sentencepiece-korean-speed": Search(
        ("SentencePiece segmentation speed Korean", "SentencePiece sentences per second Korean"),
        "SentencePiece times English and Japanese segmentation only. ONE-Piece (2021.naacl-industry.13) times"
        " Korean morphological analysers, not SentencePiece.",
    ),
    "byt5-learning-rate": Search(
        ("ByT5 pre-training learning rate schedule inverse square root", "ByT5 Adafactor learning rate warmup"),
        "ByT5 gives a constant learning rate of 0.001 for fine-tuning, not a pre-training schedule. MANTa follows"
        " ByT5's optimiser but states its own schedule.",
    ),
    "vitamin-d": Search(
        ("vitamin D recommended daily intake adults", "dietary supplement dosage IU per day"),
        "No Chunk is about nutrition; the nearest is a maths word problem that mentions Vitamin Water.",
    ),
    "world-cup-2018": Search(
        ("2018 FIFA World Cup winner", "football World Cup final France Croatia"),
        "No Chunk is about football.",
    ),
}


def cell(text: str) -> str:
    return text.replace("|", "\\|")


def main() -> None:
    questions = [question for question in load_evaluation_set(EVALUATION_SET) if not question.answerable]
    if differ := sorted({question.id for question in questions} ^ set(SEARCHES)):
        raise SystemExit(f"absence_search: SEARCHES and the unanswerable questions differ on {', '.join(differ)}")
    corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"))
    chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
    configs = load_retrieval_config().retrievers.values()
    retrievers = [(config.name, index.load(Path("data/index-cache"), corpus, config).retriever) for config in configs]
    lines = [
        "# Absence evidence for the unanswerable questions",
        "",
        f"Written by `hack/absence_search.py` (ADR 0045) over {len(corpus.chunks)} Chunks from {len(corpus.files)} files.",
        f"For each unanswerable question, the top {DEPTH} Chunks from each retriever for the question and for each probe query.",
        "A question stays unanswerable only if none of these Chunks answers it; the developer confirms each one.",
    ]
    for question in questions:
        search = SEARCHES[question.id]
        lines += ["", f"## {question.id}", "", f"> {question.question}", "", f"Drafter's reading: {search.reading}"]
        for query in [question.question, *search.probes]:
            for name, retriever in retrievers:
                lines += ["", f"### {name}: {query}", "", "| Rank | Score | Pinned id | Section | Text |", "|---:|---:|---|---|---|"]
                for rank, (chunk_id, score) in enumerate(retriever.query(query, DEPTH), start=1):
                    chunk = chunks[chunk_id]
                    text = cell(" ".join(chunk.text.split())[:SNIPPET])
                    lines.append(f"| {rank} | {score:.3f} | {chunk.pinned_id} | {cell(' › '.join(chunk.section_path))} | {text} |")
    EVIDENCE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"absence_search: {len(questions)} unanswerable questions; evidence in {EVIDENCE}")


if __name__ == "__main__":
    main()
