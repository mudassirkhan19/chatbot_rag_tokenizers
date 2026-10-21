"""Recall@5 on the chatbot's ranking (bge-small+per-paper+collapsed), with and without the reranker, for each
follow-up's Rewrite made two ways: from questions only (evaluate's rewriter row) and with answers (the committed chat run)."""
import json
from pathlib import Path
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.chat.model import load_answer_model
from chatbot_rag_tokenizers.chat.names import name_papers
from chatbot_rag_tokenizers.collection.manifest import read_manifest
from chatbot_rag_tokenizers.evaluation.config import load_matching_rule
from chatbot_rag_tokenizers.evaluation.evalset import load_evaluation_set
from chatbot_rag_tokenizers.evaluation.matching import holds
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval import index, rerank
from chatbot_rag_tokenizers.retrieval.collapse import Collapsed
from chatbot_rag_tokenizers.retrieval.config import load_retrieval_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
from chatbot_rag_tokenizers.retrieval.per_paper import NamedWorks, PerPaper

chat = load_chat_config(Path("config/retrieval.toml"))
retrieval = load_retrieval_config()
corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"), Path("data/manifest.csv"))
chunks = {c.chunk_id: c for c in corpus.chunks}
manifest = read_manifest(Path("data/manifest.csv"))
raw = index.load(Path("data/index-cache"), corpus, chat.retriever).retriever
model = load_answer_model(chat.model)
names: dict[str, tuple[str, ...]] = {}
def named(text):
    if text not in names:
        names[text] = name_papers(model, chat.names_prompt, text)
    return names[text]
works = NamedWorks(chunks, manifest)
def ranking(base):
    return Collapsed(PerPaper(base, chunks, works, named), chunks, manifest, chat.collapse_pool, chat.collapse_overlap)
plain, reranked = ranking(raw), ranking(rerank.Reranked(raw, chunks, rerank.load_scorer(retrieval.rerank), retrieval.rerank.pool))
rule = load_matching_rule(Path("config/evaluation.toml"))
report = Path("data/eval/eval-report.md").read_text()
questions_only = {}
for line in report.split("\n### Rewrites\n", 1)[1].split("\n### ", 1)[0].splitlines():
    c = [x.strip() for x in line.strip("|").split("|")]
    if len(c) == 4 and c[0] not in ("Question", "---"):
        questions_only[c[0]] = c[3]
answers = {r["question_id"]: r for r in map(json.loads, list(open("data/eval/chat-answers.jsonl"))[1:]) if r.get("scored") and r.get("type") == "follow-up"}
totals = {}
for q in load_evaluation_set(Path("data/eval/evaluation-set.jsonl")):
    if q.type != "follow-up":
        continue
    for setting, text in (("questions", questions_only[q.id]), ("answers", answers[q.id]["rewrite"])):
        cells = []
        for label, retriever in (("plain", plain), ("reranked", reranked)):
            top = [chunks[c].text for c, _ in retriever.query(text, chat.k)]
            found = sum(any(holds(t, p.quote, rule) for t in top) for p in q.passages) / len(q.passages)
            totals[setting, label] = totals.get((setting, label), 0) + found / 8
            cells.append(f"{label} {found:.2f}")
        check = f"  (chat run: {answers[q.id]['passages_found']})" if setting == "answers" else ""
        print(f"{q.id:30} {setting:9} {'  '.join(cells)}{check}")
for key, value in totals.items():
    print(key, f"Recall@5 {value:.2f}")
