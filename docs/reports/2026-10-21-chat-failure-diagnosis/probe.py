"""Rank of target Chunks for query variants, raw and collapsed. Usage: probe.py TARGETS(comma) QUERY..."""
import sys
from pathlib import Path
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval import index
from chatbot_rag_tokenizers.retrieval.collapse import Collapsed
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
from chatbot_rag_tokenizers.collection.manifest import read_manifest
cfg = load_chat_config(Path('config/retrieval.toml'))
corpus = load_corpus(load_parse_config(Path('config/parse.toml')), Path('data/parse-cache'), Path('data/parse-report.md'), Path('data/manifest.csv'))
chunks = {c.chunk_id: c for c in corpus.chunks}
raw = index.load(Path('data/index-cache'), corpus, cfg.retriever).retriever
col = Collapsed(raw, chunks, read_manifest(Path('data/manifest.csv')), cfg.collapse_pool)
targets = sys.argv[1].split(',')
for q in sys.argv[2:]:
    print('Q:', q)
    for name, r in (('raw', raw), ('collapsed', col)):
        res = [c for c, _ in r.query(q, 50)]
        ranks = {t: (res.index(t) + 1 if t in res else None) for t in targets}
        print(f'  {name}: ranks {ranks}; top5 {[chunks[c].pinned_id + ":" + c[-4:] for c in res[:5]]}')
