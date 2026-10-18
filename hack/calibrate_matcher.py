"""Calibrate the Passage matcher's threshold on real Versions (ADR 0041): `uv run python hack/calibrate_matcher.py`.

Reads data/eval/calibration.jsonl: quotes from the latest Version of three CC BY Seeds, each with whether its v1
Chunk should hold it. Reworded sentences and renumbered citations should match; a changed number, the same
words about another subject, and content added after v1 should not. For each threshold from 40% to 90% it
prints how many of each kind come out as expected against the v1 Chunks, and how loose the rule is over the
whole corpus: the Chunks outside the quote's Work that hold it. Needs the parse cache of the full run.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

from chatbot_rag_tokenizers.collection.fulltext import read_manifest
from chatbot_rag_tokenizers.evaluation.config import load_matching_rule
from chatbot_rag_tokenizers.evaluation.matching import Alignment, MatchingRule, Words, align, may_hold
from chatbot_rag_tokenizers.evaluation.works import Works
from chatbot_rag_tokenizers.parsing.config import load_parse_config
from chatbot_rag_tokenizers.retrieval.corpus import load_corpus

THRESHOLDS = [round(0.40 + 0.05 * step, 2) for step in range(11)]
KINDS = ["reworded", "citation", "number", "different", "absent"]


def main() -> None:
    items = [json.loads(line) for line in Path("data/eval/calibration.jsonl").read_text(encoding="utf-8").splitlines()]
    configured = load_matching_rule()
    corpus = load_corpus(load_parse_config(Path("config/parse.toml")), Path("data/parse-cache"), Path("data/parse-report.md"))
    works = Works(read_manifest(Path("data/manifest.csv")))
    quotes = [Words.of(item["quote"]) for item in items]
    loosest = MatchingRule(min(THRESHOLDS), configured.edge_min_words)
    # Every alignment that could pass at the loosest threshold: in the v1 file, and anywhere outside the Work.
    in_v1: dict[int, list[Alignment]] = defaultdict(list)
    elsewhere: dict[int, list[tuple[str, Alignment]]] = defaultdict(list)  # with the holding Chunk's pinned id
    for chunk in corpus.chunks:
        text = Words.of(chunk.text)
        for number, (item, quote) in enumerate(zip(items, quotes)):
            if not may_hold(text, quote, loosest) or (found := align(text, quote)) is None:
                continue
            if chunk.pinned_id == item["v1"]:
                in_v1[number].append(found)
            elif works.of(chunk.edition_id) != works.of(item["edition_id"]):
                elsewhere[number].append((chunk.pinned_id, found))
    totals = Counter(item["kind"] for item in items)
    print(f"{len(items)} quotes: " + ", ".join(f"{totals[kind]} {kind}" for kind in KINDS) + f"; edge_min_words {configured.edge_min_words}")
    print()
    print("| Threshold | " + " | ".join(KINDS) + " | as expected | quotes held outside their Work | such Chunks |")
    print("|---:|" + "---:|" * (len(KINDS) + 3))
    for threshold in THRESHOLDS:
        rule = MatchingRule(threshold, configured.edge_min_words)
        right: Counter[str] = Counter()
        for number, item in enumerate(items):
            held = any(found.meets(rule) for found in in_v1[number])
            right[item["kind"]] += held == (item["expect"] == "match")
        foreign = [sum(found.meets(rule) for _, found in elsewhere[number]) for number in range(len(items))]
        cells = [f"{right[kind]}/{totals[kind]}" for kind in KINDS]
        print(
            f"| {threshold:.2f} | {' | '.join(cells)} | {sum(right.values())}/{len(items)} |"
            f" {sum(1 for count in foreign if count)} | {sum(foreign)} |"
        )
    print()
    print(
        "Each quote against its v1 file: the best share of its words matched, and whether the numbers matched;"
        f" then the files outside its Work holding it at the configured {configured.threshold:.2f}."
    )
    for number, item in enumerate(items):
        best = max(in_v1[number], key=lambda found: found.matched / found.counted, default=None)
        share = f"{best.matched}/{best.counted} = {best.matched / best.counted:.2f}" if best else "no block"
        numbers = "" if best is None or best.numbers_match else ", numbers differ"
        holders = sorted({pinned_id for pinned_id, found in elsewhere[number] if found.meets(configured)})
        outside = f" [outside: {', '.join(holders)}]" if holders else ""
        print(f"  {item['kind']:9} {item['expect']:8} {share}{numbers}: {item['quote'][:70]}{outside}")


if __name__ == "__main__":
    main()
