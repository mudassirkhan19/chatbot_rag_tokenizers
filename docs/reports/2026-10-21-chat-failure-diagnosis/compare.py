import csv, json, collections
m = {}
for r in csv.DictReader(open('data/manifest.csv')):
    for f in r['pdf_files'].split('|'):
        if ' ' in f:
            name, h = f.rsplit(' ', 1); m[h[:16]] = (r['edition_id'], name, r['work_id'], r['canonical'])
def info(c):
    h = c.split('-')[0]; e = m.get(h, ('?','?','?','?')); return f"{c} {e[1]} work={e[2]} canon={e[3]}"
lab = {x['question_id']: x for x in csv.DictReader(open('data/eval/grounding-check.csv'))}
cur = {}
for l in open('data/eval/chat-answers.jsonl'):
    d = json.loads(l)
    if 'question_id' in d: cur[d['question_id']] = d
for q, x in lab.items():
    c = cur.get(q)
    print('=' * 20, q, '| label:', x['label'])
    print('OLD rewrite:', x['rewrite'])
    for ch in x['retrieved'].split(): print('  old', info(ch))
    if c:
        print('NEW rewrite:', c['rewrite'], '| abst', c['abstention'], 'grounded', c['grounded'], 'passages', c['passages_found'])
        for ch in c['retrieved']: print('  new', info(ch))
        print('NEW reply:', c['reply'][:700])
    dup = collections.Counter(m.get(ch.split('-')[0],('?',)*3)[2] for ch in (c['retrieved'] if c else []))
    print('NEW works in top5:', dict(dup))
