import pickle, json, csv, re, sys
d = pickle.load(open(sys.argv[1], 'rb'))
work = {r['edition_id']: r['work_id'] or 'ed:'+r['edition_id'] for r in csv.DictReader(open('data/manifest.csv'))}
def sh(t):
    w = re.findall(r'\w+', t.lower()); return {tuple(w[i:i+5]) for i in range(max(1, len(w)-4))}
def jac(a, b): A, B = sh(a), sh(b); return len(A & B) / max(1, min(len(A), len(B)))
src = sys.argv[2]
turns = dups = 0; ex = []
for l in open(src):
    x = json.loads(l)
    if 'retrieved' not in x: continue
    turns += 1; r = x['retrieved']; hit = False
    for i in range(len(r)):
        for j in range(i+1, len(r)):
            a, b = d[r[i]], d[r[j]]
            if a.file_sha256 != b.file_sha256 and work[a.edition_id] == work[b.edition_id]:
                o = jac(a.text, b.text)
                if o >= 0.5: hit = True; ex.append((x['question_id'], r[i], r[j], round(o, 2), a.section_path == b.section_path))
    dups += hit
print(f'{src}: {dups}/{turns} Turns hold a near-duplicate pair (5-gram overlap >= 0.5, different files of one Work)')
for e in ex: print('  ', e)
