"""Rank of target Chunks for query variants, under the committed [chat] retriever without its per-paper split.

Usage: probe.py TARGETS(comma) QUERY...

The ranking is dense.bge-small, then the Collapsed ranking with the [chat] pool and overlap. The per-paper split is
left out: it only changes a question that names two or more papers. The top 5 is printed so that it can be compared
with the Turn's `retrieved` in data/eval/chat-answers.jsonl. It is #77's probe.py, with the overlap that
ADR 0074 added to the Collapsed ranking, and without the raw ranking.
"""

import sys
from pathlib import Path

from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.collection.manifest import read_manifest
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval import index
from chatbot_rag_tokenizers.retrieval.collapse import Collapsed
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus

cfg = load_chat_config(Path("config/retrieval.toml"))
corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"), Path("data/manifest.csv"))
chunks = {c.chunk_id: c for c in corpus.chunks}
raw = index.load(Path("data/index-cache"), corpus, cfg.retriever).retriever
col = Collapsed(raw, chunks, read_manifest(Path("data/manifest.csv")), cfg.collapse_pool, cfg.collapse_overlap)
targets = sys.argv[1].split(",")
for q in sys.argv[2:]:
    print("Q:", q)
    res = [c for c, _ in col.query(q, 50)]
    ranks = {t: (res.index(t) + 1 if t in res else None) for t in targets}
    print(f"  collapsed ranks (of 50) {ranks}")
    print(f"  top5 {res[:5]}")
