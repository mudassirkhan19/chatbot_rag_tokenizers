# 0016. Semantic Scholar waits out long throttles

- **Date:** 2026-10-16
- **Status:** Accepted. Supersedes the retry limits for Semantic Scholar in [0008](0008-semantic-scholar-keyword-discovery.md).

## Context
We have no `S2_API_KEY`, so Seed expansion ([0009](0009-seeds-and-citation-expansion.md)) runs on Semantic Scholar's shared pool. Under [0008](0008-semantic-scholar-keyword-discovery.md) a request gets 12 attempts and waits at most 60 s between them, so a run gives up after about 6.5 min of 429s. On the first full run the pool refused requests for longer than that again and again. Three runs in a row crashed on a Seed's own record after doing one Seed each (sennrich-bpe, then sentencepiece twice). Each crash cost a restart and a wait of about 10 min, so 18 Seeds were heading for about 5 hours.

## Decision
- **Semantic Scholar backs off for up to 5 min between attempts and tries a request up to 16 times.** The wait doubles from 1 s to 256 s, then stays at 300 s, so a run waits out about 38 min of throttling before it gives up. A longer `Retry-After` is still honoured.
- The 60 s cap stays the default for every other source. `RateLimitedHttp` takes `max_backoff` per client.

## Alternatives considered
- **Keep the limits and rerun from a loop after each crash:** works, because every rerun resumes from the Snapshot. But each crash adds a process start and a fixed wait, and the loop has to tell a 429 apart from a real bug.
- **Retry forever:** a run could hang silently for hours if the pool stays shut or the key is revoked. A bound of about 40 min still ends in an error someone sees.
- **Get an API key:** the real fix, and still supported by `S2_API_KEY`, but we don't have one.

## Consequences
- A throttled run sits idle for up to about 38 min per request instead of crashing. Only the stderr line "fetching …" shows where it is waiting.
- Runs with a key or with a full Snapshot are unchanged.
