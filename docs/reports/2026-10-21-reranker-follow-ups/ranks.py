"""Where each follow-up's Passage first ranks in bge-small's top 50, raw and reranked, for its reference rewrite, its Rewrite from questions only (evaluate's rewriter row) and its Rewrite with answers (the committed chat run)."""
import json
from pathlib import Path
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval import index, rerank
from chatbot_rag_tokenizers.evaluation.evalset import load_evaluation_set
from chatbot_rag_tokenizers.evaluation.config import load_matching_rule
from chatbot_rag_tokenizers.evaluation.matching import holds

corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"), Path("data/manifest.csv"))
cfg = load_retrieval_config()
retriever = index.load(Path("data/index-cache"), corpus, cfg.retrievers["dense.bge-small"]).retriever
chunks = {c.chunk_id: c for c in corpus.chunks}
rule = load_matching_rule(Path("config/evaluation.toml"))
reranked = rerank.Reranked(retriever, chunks, rerank.load_scorer(cfg.rerank), 50)
report = Path("data/eval/eval-report.md").read_text()
rewrites = {}
for line in report.split("\n### Rewrites\n", 1)[1].split("\n### ", 1)[0].splitlines():
    c = [x.strip() for x in line.strip("|").split("|")]
    if len(c) == 4 and c[0] not in ("Question", "---"):
        rewrites[c[0]] = c[3]

with_answers = {r["question_id"]: r["rewrite"] for r in map(json.loads, list(open("data/eval/chat-answers.jsonl"))[1:]) if r.get("scored") and r.get("type") == "follow-up"}

def first(hits, q):
    return next((r for r, (cid, _) in enumerate(hits, 1) if any(holds(chunks[cid].text, p.quote, rule) for p in q.passages)), None)

for q in load_evaluation_set(Path("data/eval/evaluation-set.jsonl")):
    if q.type != "follow-up":
        continue
    texts = [("reference", q.rewrite), ("questions", rewrites[q.id]), ("answers", with_answers[q.id])]
    for kind, text in texts:
        print(f"{q.type:12} {q.id:32} {kind:8} raw {str(first(retriever.query(text, 50), q)):>4}  reranked {str(first(reranked.query(text, 50), q)):>4}  words {len(text.split())}")
