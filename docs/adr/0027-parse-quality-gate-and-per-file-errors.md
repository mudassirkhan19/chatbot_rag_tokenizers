# 0027. Parse quality gate, permanent failures and per-file errors

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
Issue #20 of the parse step (#14): garbled or empty parses must never reach the index, and a long parse run over about 5k files must always finish and report what went wrong. Scanned PDFs (no text layer) and PDFs GROBID can't read are expected in the corpus; OCR is out of scope, so they fail and are counted. The tracer ([0025](0025-parse-tracer-paragraph-packing-pinned-tokenizer-and-parse-cache.md)) left the gate between the TEI reader and the Chunker, and the error handling around the parser client.

## Decision
- **The gate.** A file fails when:
  - GROBID answers with an error (any status but 200, or an empty body), the request fails in transport, or its TEI isn't well-formed TEI with a header: reason *GROBID error*, with the status and GROBID's message;
  - GROBID gives no answer within the client's 300 s timeout: *GROBID timeout*;
  - the document has fewer than `min_sections` Sections (2; the abstract counts as one): *too few Sections*;
  - its Sections hold fewer than `min_body_characters` characters of text (2,000; the abstract counts, front matter and references don't): *too little body text*.

  The checks run in that order and the first one that fails is the reason. A failed file gets no Chunks.
- **Thresholds in `[chunking]`** of `config/parse.toml`, as #14 asks. They are part of `ChunkingConfig.describe()`, so the report lists them with the rest of the chunking config, and the chunking key ([0028](0028-parse-cache-keys-and-determinism-checks.md)) changes when they do.
- **Failures are permanent for hash, parser and config.** A failure is written to the parse cache as `<parser key>.<chunking key>.failure.json` (`reason`, `detail`, `sections`), under the same key as the Chunks would be, and any old Chunks file for that key is removed. A rerun that finds the record reports the failure again without calling GROBID or re-reading the TEI. Because the record shares the Chunks' key, a new parser image or chunking config (thresholds included) retries the file; to retry by hand, delete the `.failure.json` file.
- **Report.** The failed file's Status cell reads `failed: <reason> (<detail>)`, e.g. `failed: too few Sections (0, minimum 2)`, so the table keeps its columns. A *Quality gate* section states the rule with the thresholds used, the totals add *Parsed* and *Failed*, and *Failures by reason* counts them.
- **Per-file errors never stop the run.** Each failure is printed to stderr as it happens. After the report is written, every failed file is printed together and the exit is non-zero whenever there was one, as #14 asks and as `fetch` does. That includes failures recorded by an earlier run and not retried: they are listed in a block of their own ("2 files failed, on an earlier run. …"), after this run's, so the message still tells a new failure from a known one, but the exit doesn't. *(Amended after review: at first, recorded failures only got a one-line note and the exit stayed zero.)*
- **An unreachable service stops the run at once.** A connection error (nothing listening on the port) is not a file's fault, so nothing is recorded and no report is written: the run exits with "the GROBID service isn't reachable at http://localhost:8070. Start it with `just grobid-up` and run parse again." Files whose TEI is cached don't need the service, so the check is made by the first request, not up front.
- **`--limit N`** parses the first N input files in pinned-id order, the order the run uses anyway, so a smoke test is deterministic. The report then covers those files only.

## Alternatives considered
- **Retry failures on every run, as `fetch` does.** A fetch failure is usually the network and a retry fixes it. A GROBID failure on the same bytes, parser and config is deterministic, so a retry only costs time (up to 300 s per file for a timeout).
- **Exit zero when every failure was recorded by an earlier run.** It was the first choice, so that a rerun over a corpus with a few scanned PDFs that can never pass succeeds. But #14 asks for a non-zero exit whenever there were failures, and a zero exit would let a script or CI step treat a corpus with unparsed files as complete. The separate block in the message keeps the "something new went wrong" signal for a person reading it.
- **Check `/api/isalive` before the run.** It would fail a fully cached rerun that needs no service.
- **A separate `[quality]` config section.** Clearer on its own, but #14 puts the thresholds in the chunking config, and keeping them there makes them part of the key the outcome is cached under.
- **A Reason column in the report table.** It would be empty for nearly every row and change the table every parse ticket extends.

## Consequences
- A file that fails at a 300 s timeout is never retried under the same key, even if the service was only slow that once. Deleting its `.failure.json` retries it.
- A changed threshold or other chunking setting retries every recorded failure under the new key, GROBID failures included, since they are recorded per chunking key too. That costs a GROBID call per failed file, which is rare enough not to need a second, parser-only record.
- The trimmed fixtures `near-empty.tei.xml` and `scanned.tei.xml` are cut from GROBID's TEI for Sennrich et al. v5 (CC BY 4.0), with funders and the bibliography removed and the request time fixed.
- **Thresholds checked on the Seeds (#23), and kept.** All 34 Seed PDFs pass with a wide margin: the fewest Sections is 6 (2004.03720v1) and the least Section text is 15,554 characters (the same file), against minimums of 2 and 2,000. An image-only PDF made from Sennrich v5's first page fails before the gate, as *GROBID error* (`HTTP 500: [NO_BLOCKS] PDF parsing resulted in empty content`). The Seeds are all good papers, so they can't show the gate is too lenient; raising the minimums would only risk failing short papers (a 4-page workshop paper has about 12,000 characters). Revisit after the full-corpus run, from the report's failures and the smallest passing files.
