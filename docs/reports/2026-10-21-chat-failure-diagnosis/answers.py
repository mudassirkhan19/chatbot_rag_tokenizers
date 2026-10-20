import json, pickle, sys
from pathlib import Path
from chatbot_rag_tokenizers.chat.config import load_chat_config
from chatbot_rag_tokenizers.chat.model import load_answer_model
from chatbot_rag_tokenizers.chat.answer import messages, read_answer
cfg = load_chat_config(Path('config/retrieval.toml'))
m = load_answer_model(cfg.model)
chunks = pickle.load(open(sys.argv[1], 'rb'))
L = [json.loads(l) for l in open('data/eval/chat-answers.jsonl')][1:]
base = cfg.system_prompt.replace('{abstention}', cfg.abstention)
strict = base.replace('5. Answer in a few sentences of plain text.',
 '5. If the question names a language, model, paper or setting, use only Chunks about that one. A fact about another language, model or setting is not an answer; if that is all the Chunks hold, reply with the sentence in rule 4.\n'
 '6. Each Chunk comes from the paper named in its header. Never give one paper\'s explanation as the reason for another paper\'s result.\n'
 '7. Answer in a few sentences of plain text.')
for qid in sys.argv[2:]:
    t = [x for x in L if x['question_id'] == qid]
    earlier = [(x['rewrite'] or x['question'], read_answer(x['reply'], 5, cfg.abstention).text) for x in t[:-1]][-3:]
    last = t[-1]; rc = [chunks[c] for c in last['retrieved']]
    q = last['rewrite'] or last['question']
    for name, p in (('base', base), ('strict', strict)):
        print(f'{qid} [{name}]:', m.complete(messages(p, q, rc, earlier)).replace('\n', ' ')[:500])
