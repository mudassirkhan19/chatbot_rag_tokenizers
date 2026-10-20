import pickle, sys
d = pickle.load(open(sys.argv[1], 'rb'))
for c in sys.argv[2:]:
    ch = d[c]; print(f"--- {c} [{ch.pinned_id}] {ch.section_path} {ch.kind}\n  H: {ch.header}\n  {ch.text[:int(__import__('os').environ.get('N','600'))]}\n")
