"""How the Collapsed ranking's copy rule (ADR 0072) splits the corpus: for every Chunk of a Work with more than one
file, its best and second-best word 5-gram overlap (on the smaller Chunk) with a Chunk of each other file of the
Work, and how many pairs at or above the threshold the closest-Chunk condition keeps apart.

uv run python docs/reports/2026-10-21-collapse-by-text/overlaps.py <chunks.pkl> [threshold]
(<chunks.pkl> from docs/reports/2026-10-21-chat-failure-diagnosis/chunks.py)
"""
import collections, csv, pickle, re, sys

chunks = pickle.load(open(sys.argv[1], "rb"))
threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
work = {r["edition_id"]: r["work_id"] or "ed:" + r["edition_id"] for r in csv.DictReader(open("data/manifest.csv"))}


def shingles(text):
    w = re.findall(r"\w+", text.lower())
    return frozenset(tuple(w[i : i + 5]) for i in range(max(1, len(w) - 4)))


files = collections.defaultdict(lambda: collections.defaultdict(list))  # work -> file -> chunk ids
for c in chunks.values():
    files[work[c.edition_id]][c.file_sha256].append(c.chunk_id)
best, second = collections.Counter(), collections.Counter()
closest = {}  # (chunk id, file) -> its highest overlap with that file's Chunks
pairs = {}  # (chunk id, chunk id) -> overlap, for the pairs at or above the threshold
for by_file in files.values():
    if len(by_file) < 2:
        continue
    sh = {i: shingles(chunks[i].text) for ids in by_file.values() for i in ids}
    for f, ids in by_file.items():
        for g, others in by_file.items():
            if f == g:
                continue
            index = collections.defaultdict(set)
            for d in others:
                for s in sh[d]:
                    index[s].add(d)
            for c in ids:
                shared = collections.Counter(d for s in sh[c] for d in index.get(s, ()))
                scores = {d: n / max(1, min(len(sh[c]), len(sh[d]))) for d, n in shared.items()}
                ranked = sorted(scores.values(), reverse=True) + [0.0, 0.0]
                best[min(9, int(ranked[0] * 10))] += 1
                second[min(9, int(ranked[1] * 10))] += 1
                closest[c, g] = ranked[0]
                pairs.update({(c, d): o for d, o in scores.items() if o >= threshold})
print(f"{sum(best.values())} (Chunk, other file of its Work) pairs")
print("overlap   best match   second-best match")
for b in range(10):
    print(f"{b / 10:.1f}-{(b + 1) / 10:.1f}   {best[b]:>9}   {second[b]:>9}")
kept_apart = [(c, d, o) for (c, d), o in pairs.items() if c < d and o < closest[c, chunks[d].file_sha256] and o < closest[d, chunks[c].file_sha256]]
print(f"{len(pairs) // 2} pairs at or above {threshold}; the closest-Chunk condition keeps {len(kept_apart)} of them apart, e.g.:")
for c, d, o in sorted(kept_apart)[:10]:
    print(f"   {c} {d} {o:.2f}  {chunks[c].section_path[-1][:40]!r} / {chunks[d].section_path[-1][:40]!r}")
