import json
from pathlib import Path
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.chat.model import load_answer_model
from chatbot_rag_tokenizers.chat.rewrite import rewrite
from chatbot_rag_tokenizers.chat.answer import read_answer
cfg = load_chat_config(Path('config/retrieval.toml'))
m = load_answer_model(cfg.model)
L = [json.loads(l) for l in open('data/eval/chat-answers.jsonl')][1:]
SHARP = cfg.rewrite_prompt + ' Always name the method, model or paper the question is about, as the conversation names it, so the question could be searched on its own.'
for qid in ('wechsel-neighbours', 'vocabulary-with-scarce-data', 'code-tokenizer-initialisation', 'canine-hashing', 'digits-fourth-digit'):
    t = [x for x in L if x['question_id'] == qid]
    first, follow = t[0], t[-1]
    ans = read_answer(first['reply'], 5, cfg.abstention).text
    print(qid)
    print('  production (Q+A):', rewrite(m, cfg.rewrite_prompt, [(first['question'], ans)], follow['question']))
    print('  questions only   :', rewrite(m, cfg.rewrite_prompt, [(first['question'], '')], follow['question']))
    print('  sharper prompt   :', rewrite(m, SHARP, [(first['question'], ans)], follow['question']))
