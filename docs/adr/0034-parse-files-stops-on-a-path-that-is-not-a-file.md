# 0034. `parse --files` stops on a path that isn't a file

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
Issue #25: `parse --files no/such/file.pdf` stopped with a Python traceback (`FileNotFoundError` in `from_paths`). The same happened for a directory. The record route already handles a missing file ([0031](0031-parse-reads-the-full-text-record.md)): it parses the other files, then lists the missing ones and exits non-zero. The issue allowed either that, or a one-line error before anything is parsed.

The two routes differ in why a file can be missing. In the record route, a missing file is local state, such as an unfinished fetch or a fresh clone, and `just fetch` fixes it. A `--files` path is typed by hand, so a missing one is a mistake in the command: a typo, the wrong working directory, or a glob that matched less than expected. The fix is to correct the command.

## Decision
- **Check every path before reading any.** `from_paths` raises `NotFiles` when any `--files` path isn't a file, naming each one with what is there instead (`no such file` or `a directory`). The CLI prints it and exits 1:

  ```
  parse: 2 paths given with --files aren't files; nothing was parsed:
    no/such/file.pdf: no such file
    data/pdfs: a directory
  ```

- **Nothing is parsed, cached or reported.** No GROBID call is made, no cache entry is written, and the report is left as it was.

## Alternatives considered
- **Parse the other files and list the missing ones at the end, as the record route does.** The two routes would behave the same, but on `--files` the files given decide each other's Editions ([0032](0032-chunks-carry-their-edition-id.md)): an arXiv Version's Edition is the latest Version given. With v2 mistyped, v1 would be parsed as its own Edition and its Chunks cached with the wrong Edition id. A run without `--limit` would also replace the committed `data/parse-report.md` with a report on fewer files, and spend GROBID time on a command that has to be rerun anyway.
- **Check each path in argparse (a `type=` function).** It stops at the first bad path and exits 2 with the usage line, so a person with several typos fixes them one run at a time.

## Consequences
- The record route is unchanged: missing or mismatched recorded files are still listed after the others are parsed.
- A path that exists but can't be read (permissions) still gives a traceback when it is read. It hasn't happened yet; it can join `NotFiles` if it does.
