"""The `collect` run: keyword queries and citation expansion → Snapshot → Editions → ACL Editions
→ rule pre-filter → arXiv records → LLM judge → manifest and funnel report, with the Fetcher's
recorded PDFs, then the checks on the Snapshot's size and that it holds no API key."""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from . import fulltext, judge, report
from .acl_anthology import AclAnthologySource
from .arxiv import ArxivSource
from .config import ScopeConfig
from .editions import Edition, combine
from .judge import JudgeVerdict, VerdictCache, question_hash
from .manifest import manifest_row, write_manifest
from .openalex import API_KEY_ENV as OPENALEX_KEY_ENV
from .openalex import OpenAlexSource
from .rules import RuleFilter, RuleOutcome
from .semantic_scholar import API_KEY_ENV as S2_KEY_ENV
from .semantic_scholar import SemanticScholarSource
from .snapshot import SnapshotStore, check_credentials, check_size

SAVE_VERDICTS_EVERY = 25  # Candidates scored between saves of the verdict cache
API_KEY_ENVS = (OPENALEX_KEY_ENV, S2_KEY_ENV)


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
    for query in config.enabled_queries():
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
        edition.withdrawn = record.withdrawn
        if done % 100 == 0:
            print(f"  arxiv: {done}/{len(preprints)} records", file=sys.stderr)
    print(f"arxiv: {len(preprints)} records", file=sys.stderr)


def add_acl_editions(editions: list[Edition], acl: AclAnthologySource) -> None:
    """Give every reported ACL ID a venue Edition built from its ACL Anthology page.

    A venue Edition a source already found under that ACL ID or the Anthology's DOI is updated
    in place; the Anthology is the authority for it. Otherwise, for example when only a preprint
    reported the ACL ID, a new venue Edition is added. It is never combined with the preprint:
    the two stay linked only by the identifiers both carry. The venue Edition is credited to every
    Discovery channel whose Candidates reported its ACL ID.
    """
    reporters: dict[str, list[Edition]] = {}  # ACL ID → Editions that reported it, in order found
    venues: dict[str, Edition] = {}  # match key → venue Edition
    for edition in editions:
        if acl_id := edition.reported_acl_id:
            reporters.setdefault(acl_id, []).append(edition)
        if edition.edition_kind == "venue":
            for key in edition.match_keys():
                venues.setdefault(key, edition)

    added = 0
    for done, (acl_id, reported_by) in enumerate(reporters.items(), 1):
        record = acl.record(acl_id)
        if done % 100 == 0:
            print(f"  acl-anthology: {done}/{len(reporters)} pages", file=sys.stderr)
        if record is None:
            continue
        venue = venues.get(f"acl:{acl_id}")
        if venue is None and (by_doi := venues.get(f"doi:{record.doi.lower()}")) and by_doi.acl_id in ("", acl_id):
            venue = by_doi  # never take over a row that names a different ACL Edition
        if venue is None:
            venue = Edition(edition_id=acl_id, edition_kind="venue", title="", abstract="", authors=[], year="")
            editions.append(venue)
            added += 1
        venue.edition_id = venue.acl_id = acl_id
        venue.title = record.title
        venue.authors = record.authors
        # Many older Anthology papers have no abstract. The reporting source's abstract describes
        # the same Work, and without one the rules and the judge would see only the title.
        venue.abstract = record.abstract or venue.abstract or next((e.abstract for e in reported_by if e.abstract), "")
        venue.year = record.year
        venue.venue = "|".join(record.venues)
        venue.doi = record.doi
        venue.licence = record.licence
        venue.source_link = record.source_link
        venue.pdf_link = record.pdf_link
        for edition in reported_by:
            venue.discovery_channels |= edition.discovery_channels
    print(f"acl-anthology: {len(reporters)} ACL IDs, {added} new venue Editions", file=sys.stderr)


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
    current_question = question_hash(config.judge)
    for start in range(0, len(to_score), SAVE_VERDICTS_EVERY):
        batch = to_score[start : start + SAVE_VERDICTS_EVERY]
        for edition, p_yes in zip(batch, model.score(batch), strict=True):
            verdict = JudgeVerdict(edition.edition_id, config.judge.model, config.judge.revision, current_question, p_yes)
            cache.put(verdict)
            verdicts[edition.edition_id] = verdict
        cache.save()
        print(f"  judge: scored {start + len(batch)}/{len(to_score)}", file=sys.stderr)
    return verdicts


@dataclass(frozen=True)
class Assessed:
    """A Candidate with both stages of its Relevance verdict: the rule outcome and, if it passed, the judge's."""

    edition: Edition
    outcome: RuleOutcome
    verdict: JudgeVerdict | None

    def manifest_row(self, threshold: float) -> dict[str, str]:
        return manifest_row(self.edition, self.outcome, self.verdict, threshold)


def assess(config: ScopeConfig, snapshot_dir: Path, refresh: bool = False, run_judge: bool = True) -> list[Assessed]:
    """Discover the Candidates, fetch their arXiv records, and apply the rules and the judge."""
    snapshot = SnapshotStore(snapshot_dir)
    arxiv = ArxivSource(snapshot, page_size=config.arxiv_page_size)
    s2 = SemanticScholarSource(snapshot, fields_of_study=config.s2_fields_of_study)
    openalex = OpenAlexSource(snapshot)
    editions = discover(config, {"arxiv": arxiv, "semantic-scholar": s2, "openalex": openalex}, s2)
    # Before the rules, so ACL Editions get a Relevance verdict like every other row.
    add_acl_editions(editions, AclAnthologySource(snapshot))
    rules = RuleFilter(config)
    outcomes = [rules.apply(edition) for edition in editions]
    passed = [edition for edition, outcome in zip(editions, outcomes, strict=True) if outcome.passed]
    # Only rule passes get their arXiv record; a reject keeps the id its source reported.
    add_arxiv_records(passed, arxiv)
    # A withdrawn preprint is excluded on its record alone, so the judge never scores it.
    to_judge = [edition for edition in passed if not edition.withdrawn]
    verdicts = judge_candidates(config, to_judge, VerdictCache(snapshot_dir), refresh, run_judge)
    return [
        Assessed(edition, outcome, verdicts.get(edition.edition_id))
        for edition, outcome in zip(editions, outcomes, strict=True)
    ]


def collect(
    config: ScopeConfig,
    snapshot_dir: Path,
    manifest_path: Path,
    report_path: Path,
    refresh: bool = False,
    run_judge: bool = True,
) -> None:
    assessed = assess(config, snapshot_dir, refresh, run_judge)
    # Before anything is written, so a leaked key never comes with a fresh manifest to commit.
    check_credentials(snapshot_dir, API_KEY_ENVS)
    rows = [candidate.manifest_row(config.judge.threshold) for candidate in assessed]
    fulltext.apply_record(rows, fulltext.FulltextRecord(snapshot_dir))
    write_manifest(manifest_path, rows)
    report.write(report_path, rows)
    report.summarise(rows, config.judge.threshold)
    check_size(snapshot_dir)
    print(f"manifest: wrote {manifest_path}, report: wrote {report_path}", file=sys.stderr)
