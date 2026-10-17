# 0030. Parse cache keys and determinism checks

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
#21 asks that cached parse results are always right and always reproducible ([0027](0027-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md) built the cache). Changing the parser must re-parse. Changing the chunking config must only re-chunk, so tuning the Chunk size during the embedding comparison stays cheap. The same inputs must give byte-identical Chunks and parse report. GROBID's raw TEI is not byte-stable ([0024](0024-grobid-stays-the-parser-after-the-docling-spike.md)): the request time, random funder ids and a figure's graphic change from parse to parse.

## Decision
- **Two keys.** In each file's folder (`<cache>/<sha256>/`):
  - the TEI is `<parser key>.tei.xml`. It is keyed by the file hash and the parser version, as 0027 set up. The parser key is `grobid-<tag>-<first 12 hex digits of the image digest>`, so a new image digest re-parses and keeps the old image's TEI beside the new one.
  - the Chunks are `<parser key>.<chunking key>.chunks.jsonl`. They are keyed by the file hash, the parser version and the chunking-config hash. The chunking key is `chunking-<first 12 hex digits of the sha256 of ChunkingConfig.describe() as sorted-key JSON>`. `describe()` is the same set of settings the report prints, so any setting added there (such as #20's quality-gate thresholds) changes the key. The tokenizer file's location is left out, because it doesn't change the Chunks; its sha256 is in.
- **A record that depends on the config goes under both keys.** `ParseCache` has `_parser_path` for records of the parse alone and `_chunking_path` for records of the parse under a config. #20's failure records use one or the other, as the failure depends on GROBID alone or on the quality gate's thresholds too.
- **Chunks are still rebuilt from the cached TEI on every run** (0027), and written under their key. Rebuilding takes milliseconds per file and keeps the Chunks matching the current code as well as the config, which a key cannot promise without a hand-maintained code version. Keying them by config keeps each config's Chunks side by side, so two Chunk sizes can be compared from one cache, and a config's Chunks are never read as another's.
- **Deterministic output.** Files are processed in pinned-id order (then hash), whatever order they are given in. Chunks are JSON with sorted keys, one per line. The cache and the report are written as UTF-8 with `\n` line ends, so the bytes don't depend on the machine's locale. Nothing in the Chunks or the report holds a time, a path or a machine name.
- **Tests at the CLI seam** (`tests/test_parse_cache.py`, offline against the fake GROBID service):
  - a chunking-config change re-chunks without calling GROBID, and the old config's Chunks stay where they were;
  - a new image digest re-parses;
  - two runs from empty caches in different places, with the files in the other order and with GROBID's answers differing in their time stamp and funder ids, give byte-identical Chunks and report; a warm rerun rewrites the same bytes.
- **Opt-in integration test** (`tests/test_parse_grobid.py`), skipped unless `RUN_GROBID_TESTS=1`. It sends `data/pdfs/seeds/wechsel_2112.06598v2.pdf` to the running container twice, each time from an empty cache, checks that the file is `parsed` with at least 2 Sections, and checks that the two runs' Chunks and reports are byte-identical. The TEI is not compared, for the reason in 0024. It fails, rather than skips, when it was asked for and GROBID or the PDF is missing.

## Alternatives considered
- **Reusing the cached Chunks instead of rebuilding them.** Faster by milliseconds, but a change to the TEI reader or the Chunker would leave stale Chunks unless a code version were also in the key and someone remembered to bump it.
- **One Chunks file per file, overwritten on a config change.** Simpler, but switching between two Chunk sizes would re-chunk every time, and nothing would show which config a Chunks file belongs to.
- **Hashing the whole config file.** It would re-chunk on a GROBID-port or comment change. `describe()` holds exactly the settings that decide the Chunks.
- **A pytest marker and a `--run-grobid` option.** It needs edits to the shared conftest and pytest config. An environment variable read in the test file is enough for one test.
- **Prior work (research-bot).** Its extractor keeps one folder of output per paper id, not per file hash, and re-extracts only when the extraction method's name changes (`src/services/pdf_extractor.py`); it records an extraction date. The same idea of a parser name deciding a re-parse, but a re-downloaded file or a new release of the same parser would not re-parse, and the date breaks byte-identical output. We keep nothing from it here.

## Consequences
- Old parser and config versions leave their files in the cache. It is local and can be deleted at any time; a run only reads the current keys.
- The report doesn't name the chunking key. The config it prints is what the key hashes.
- The integration test takes about 30 s with the container warm. Run it after changing the GROBID pin, the request or the TEI reader.
