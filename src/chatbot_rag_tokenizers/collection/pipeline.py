"""The `collect` run: keyword queries and citation expansion → Snapshot → Editions → rule pre-filter
→ arXiv records → LLM judge → manifest."""

import sys
from collections import Counter
from pathlib import Path
from typing import Protocol

from . import judge
from .arxiv import ArxivSource
from .config import ScopeConfig, is_citation_channel, is_keyword_channel
from .editions import Edition, combine
from .judge import JudgeVerdict, VerdictCache, prompt_hash
from .manifest import manifest_row, write_manifest
from .rules import RuleFilter
from .semantic_scholar import SemanticScholarSource
from .snapshot import SnapshotStore

SAVE_VERDICTS_EVERY = 25  # Candidates scored between saves of the verdict cache


class KeywordSource(Protocol):
    def search(self, query: str) -> list[Edition]: ...


class SeedSource(Protocol):
    def paper(self, paper: str) -> Edition: ...
    def references(self, paper: str) -> list[Edition]: ...
    def citations(self, paper: str) -> list[Edition]: ...


class _EditionIndex:
    """Editions seen so far, findable by every exact identifier any of their Candidates had."""

    def __init__(self) -> None:
        self._editions: list[Edition] = []  # in the order they were first found
        self._keys: dict[int, set[str]] = {}  # id(edition) → its keys, including absorbed ones
        self._by_key: dict[str, Edition] = {}

    def add(self, candidate: Edition) -> None:
        found = {id(e) for key in candidate.match_keys() if (e := self._by_key.get(key))}
        matches = [e for e in self._editions if id(e) in found]
        combined = candidate
        if matches:
            combined = matches[0]
            for other in [*matches[1:], candidate]:
                combined = combine(combined, other)
        keys = set(candidate.match_keys()) | set(combined.match_keys())
        for part in matches:
            keys |= self._keys.pop(id(part))
        if found:
            self._editions = [e for e in self._editions if id(e) not in found]
        self._editions.append(combined)
        self._keys[id(combined)] = keys
        for key in keys:
            self._by_key[key] = combined

    def editions(self) -> list[Edition]:
        return list(self._editions)


def discover(config: ScopeConfig, sources: dict[str, KeywordSource], seed_source: SeedSource) -> list[Edition]:
    """Run every keyword query, then expand one hop from every Seed, and combine Candidates that are
    the same Edition, keeping all their channels.

    Expansion adds the Seed's own record and the papers it cites and that cite it, each tagged
    with a channel naming the Seed.

    Candidates combine only on an exact identifier for that Edition (see ``Edition.match_keys``),
    so a preprint and its venue Edition stay two rows. A preprint revised between two page
    fetches shows up under two Versions; it is still one Edition. Its pin comes later, from the
    full arXiv record.
    """
    index = _EditionIndex()
    for query in config.queries:
        found = sources[query.source].search(query.query)
        for edition in found:
            edition.discovery_channels.add(query.discovery_channel)
            index.add(edition)
        print(f"discover: {query.discovery_channel} found {len(found)} Candidates", file=sys.stderr)
    for seed in config.seeds:
        expansion = [
            (seed.discovery_channel, [seed_source.paper(seed.paper)]),
            (seed.references_channel, seed_source.references(seed.paper)),
            (seed.citations_channel, seed_source.citations(seed.paper)),
        ]
        for channel, found in expansion:
            for edition in found:
                edition.discovery_channels.add(channel)
                index.add(edition)
            print(f"discover: {channel} found {len(found)} Candidates", file=sys.stderr)
    return index.editions()


def add_arxiv_records(editions: list[Edition], arxiv: ArxivSource) -> None:
    """Give every arXiv Edition in ``editions``, whichever channel found it, its full record from arXiv.

    The record is the authority: the Edition is re-pinned to the latest Version it lists, and
    its comments and licence replace whatever the finding source reported.
    """
    preprints = [edition for edition in editions if edition.edition_kind == "arxiv-preprint"]
    for done, edition in enumerate(preprints, 1):
        record = arxiv.record(edition.arxiv_id)
        edition.edition_id = f"{edition.arxiv_id}{record.latest_version}"
        edition.source_link = f"https://arxiv.org/abs/{edition.edition_id}"
        edition.versions = record.versions
        edition.arxiv_comments = record.comments
        edition.licence = record.licence
        if done % 100 == 0:
            print(f"  arxiv: {done}/{len(preprints)} records", file=sys.stderr)
    print(f"arxiv: {len(preprints)} records", file=sys.stderr)


def judge_candidates(
    config: ScopeConfig, editions: list[Edition], cache: VerdictCache, refresh: bool, run_judge: bool
) -> dict[str, JudgeVerdict]:
    """The judge verdict for each Edition, by Edition id.

    Cached verdicts made with the configured model, revision and prompt are reused unless
    ``refresh`` is set. The rest are scored and the cache is saved every few Candidates, so an
    interrupted run keeps its progress. With ``run_judge`` off they are left without a verdict and
    the model is never loaded.
    """
    verdicts: dict[str, JudgeVerdict] = {}
    to_score: list[Edition] = []
    for edition in editions:
        cached = None if refresh else cache.get(edition.edition_id, config.judge)
        if cached is None:
            to_score.append(edition)
        else:
            verdicts[edition.edition_id] = cached
    print(f"judge: {len(verdicts)} cached verdicts, {len(to_score)} to score", file=sys.stderr)
    if not to_score or not run_judge:
        return verdicts

    model = judge.load_judge(config.judge)
    current_prompt = prompt_hash(config.judge.prompt)
    for start in range(0, len(to_score), SAVE_VERDICTS_EVERY):
        batch = to_score[start : start + SAVE_VERDICTS_EVERY]
        for edition, p_yes in zip(batch, model.score(batch), strict=True):
            verdict = JudgeVerdict(edition.edition_id, config.judge.model, config.judge.revision, current_prompt, p_yes)
            cache.put(verdict)
            verdicts[edition.edition_id] = verdict
        cache.save()
        print(f"  judge: scored {start + len(batch)}/{len(to_score)}", file=sys.stderr)
    return verdicts


def _report_expansion(rows: list[dict[str, str]]) -> None:
    """What citation expansion adds beyond keyword search, in Editions and in included Editions.

    A Seed's own record counts as neither: it was picked by hand, not found.
    """

    keyword, expanded, expansion_only = [], [], []
    for row in rows:
        channels = row["discovery_channels"].split("|")
        found_by_keyword = any(is_keyword_channel(channel) for channel in channels)
        if found_by_keyword:
            keyword.append(row)
        if any(is_citation_channel(channel) for channel in channels):
            expanded.append(row)
            if not found_by_keyword:
                expansion_only.append(row)

    def included(group: list[dict[str, str]]) -> int:
        return sum(row["relevance_verdict"] == "included" for row in group)

    print(f"  keyword search: {len(keyword)} Editions, {included(keyword)} included", file=sys.stderr)
    print(
        f"  citation expansion: {len(expanded)} Editions, {len(expansion_only)} found by no keyword query,"
        f" {included(expansion_only)} of those included",
        file=sys.stderr,
    )


def collect(
    config: ScopeConfig, snapshot_dir: Path, manifest_path: Path, refresh: bool = False, run_judge: bool = True
) -> None:
    snapshot = SnapshotStore(snapshot_dir)
    arxiv = ArxivSource(snapshot, page_size=config.arxiv_page_size)
    s2 = SemanticScholarSource(snapshot, fields_of_study=config.s2_fields_of_study)
    editions = discover(config, {"arxiv": arxiv, "semantic-scholar": s2}, s2)
    rules = RuleFilter(config)
    outcomes = [rules.apply(edition) for edition in editions]
    passed = [edition for edition, outcome in zip(editions, outcomes, strict=True) if outcome.passed]
    # Only rule passes get their arXiv record; a reject keeps the id its source reported.
    add_arxiv_records(passed, arxiv)
    verdicts = judge_candidates(config, passed, VerdictCache(snapshot_dir), refresh, run_judge)
    threshold = config.judge.threshold
    rows = [
        manifest_row(edition, outcome, verdicts.get(edition.edition_id), threshold)
        for edition, outcome in zip(editions, outcomes, strict=True)
    ]
    write_manifest(manifest_path, rows)

    rejected = Counter(row["rule_pattern"] for row in rows if row["rule_outcome"] == "reject")
    print(f"discover: {len(rows)} Editions", file=sys.stderr)
    per_channel = Counter(channel for edition in editions for channel in edition.discovery_channels)
    only_here = Counter(next(iter(e.discovery_channels)) for e in editions if len(e.discovery_channels) == 1)
    for channel in sorted(per_channel):
        print(f"  {channel}: {per_channel[channel]} Editions, {only_here[channel]} found by no other channel", file=sys.stderr)
    _report_expansion(rows)
    print(f"rules: {len(rows) - rejected.total()} passed, {rejected.total()} rejected", file=sys.stderr)
    for pattern, count in sorted(rejected.items()):
        print(f"  {pattern}: {count}", file=sys.stderr)
    judged = Counter(row["relevance_verdict"] for row in rows if row["rule_outcome"] == "pass")
    print(
        f"judge: {judged['included']} included, {judged['excluded']} excluded, {judged['pending']} pending"
        f" (threshold {threshold:g})",
        file=sys.stderr,
    )
    print(f"manifest: wrote {manifest_path}", file=sys.stderr)
