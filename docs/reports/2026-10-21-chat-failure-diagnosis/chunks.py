import pickle, sys
from pathlib import Path
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus
c = load_corpus(load_parse_config(Path('config/parse.toml')), Path('data/parse-cache'), Path('data/parse-report.md'), Path('data/manifest.csv'))
pickle.dump({ch.chunk_id: ch for ch in c.chunks}, open(sys.argv[1], 'wb'))
print(len(c.chunks))
