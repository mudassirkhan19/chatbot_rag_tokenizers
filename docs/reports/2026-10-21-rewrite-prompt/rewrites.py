"""#82: rewrite each Evaluation-set follow-up with each candidate prompt, shown its history two ways, and score
Recall@5 on the [chat] retriever. "questions": the stored history questions, as `evaluate` shows them; "answers":
those questions with the committed chat run's answers, as `chat-eval` shows them. Prints both.
Usage: rewrites.py PROMPTS.py [names...]; "production" is the config's prompt."""
import json
import runpy
import sys
from pathlib import Path
from chatbot_rag_tokenizers.chat.answer import read_answer
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.chat.model import load_answer_model
from chatbot_rag_tokenizers.chat.rewrite import rewrite
from chatbot_rag_tokenizers.collection.manifest import read_manifest
from chatbot_rag_tokenizers.evaluation.config import load_matching_rule
from chatbot_rag_tokenizers.evaluation.evalset import load_evaluation_set
from chatbot_rag_tokenizers.evaluation.matching import holds
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval import index
from chatbot_rag_tokenizers.retrieval.collapse import Collapsed
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus

cfg = load_chat_config(Path('config/retrieval.toml'))
prompts = {'production': cfg.rewrite_prompt, **runpy.run_path(sys.argv[1])['PROMPTS']}
names = sys.argv[2:] or list(prompts)
rule = load_matching_rule(Path('config/evaluation.toml'))
follow = [q for q in load_evaluation_set(Path('data/eval/evaluation-set.jsonl')) if q.type == 'follow-up']
records = [json.loads(line) for line in open('data/eval/chat-answers.jsonl')][1:]
answered = {}
for q in follow:
    turns = [r for r in records if r['question_id'] == q.id][:-1]
    answered[q.id] = [(r['question'], read_answer(r['reply'], cfg.k, cfg.abstention).text) for r in turns][-cfg.history:]
corpus = load_corpus(load_parse_config(Path('config/parse.toml')), Path('data/parse-cache'), Path('data/parse-report.md'), Path('data/manifest.csv'))
chunks = {c.chunk_id: c for c in corpus.chunks}
raw = index.load(Path('data/index-cache'), corpus, cfg.retriever).retriever
retriever = Collapsed(raw, chunks, read_manifest(Path('data/manifest.csv')), cfg.collapse_pool)
model = load_answer_model(cfg.model)

def found(q, text):
    top = [chunks[c].text for c, _ in retriever.query(text, 5)]
    return sum(any(holds(t, p.quote, rule) for t in top) for p in q.passages), len(q.passages)

for name in names:
    rows = []
    for q in follow:
        row = {'id': q.id}
        for setting, earlier in (('questions', [(a, '') for a in q.history[-cfg.history:]]), ('answers', answered[q.id])):
            text = rewrite(model, prompts[name], earlier, q.question)
            f, n = found(q, text)
            row[setting] = {'rewrite': text, 'found': f, 'passages': n}
        rows.append(row)
    print(f'== {name}')
    for s in ('questions', 'answers'):
        recall = sum(r[s]['found'] / r[s]['passages'] for r in rows) / len(rows)
        print(f'  {s}: Recall@5 {recall:.2f}')
    for r in rows:
        print(f"  {r['id']}\n    Q: [{r['questions']['found']}] {r['questions']['rewrite']}\n    A: [{r['answers']['found']}] {r['answers']['rewrite']}")
