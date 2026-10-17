# 0036. A reset or dropped GROBID connection stops the run, like a refused one

- **Date:** 2026-10-18
- **Status:** Accepted

## Context
[0029](0029-parse-quality-gate-and-per-file-errors.md) stops the run when GROBID is unreachable and records a per-file failure for anything else that goes wrong with a request. "Unreachable" meant a refused connection (`httpx.ConnectError`) only. Every other transport error became the file's *GROBID error*, and that failure is permanent for the hash, parser and config.

Issue #28 hit the gap. Docker Desktop updated and stopped the GROBID container just after `just grobid-up` reported it up. Each remaining file then failed with `GROBID error (ReadError: [Errno 54] Connection reset by peer)` and stayed failed until a rerun with `--retry-failed`, and the committed report listed every one as failed. A connection that is reset or closed without an answer means the service has gone away, just as a refused one means it isn't there. The PDF isn't at fault: GROBID answers a PDF it can't read with an HTTP error (500 `[BAD_INPUT_DATA]`, `[NO_BLOCKS]`).

## Decision
- **A request that fails at the network level stops the run as *GROBID unreachable*.** That covers a refused, reset or broken connection (`httpx.NetworkError`: `ConnectError`, `ReadError`, `WriteError`, `CloseError`) and a connection closed without a response (`httpx.RemoteProtocolError`). As in 0029, nothing is recorded for the file, no report is written, and the run exits with "the GROBID service isn't reachable at … Start it with `just grobid-up` and run parse again." The Chunks of the files parsed before the stop stay in the cache, so a plain rerun goes on from there.
- **What stays a failure of the file:** an HTTP error answer, an empty or unreadable answer, a timeout (*GROBID timeout*), and any other transport error (a proxy or protocol error on our side).

## Alternatives considered
- **Retry a reset once before deciding.** When a container stops, the retry fails the same way, so it only delays the stop. It also leaves the case where a retry does succeed, which would mean something flaky between client and service that hides a problem. A single retry doesn't change which way to decide after it fails.
- **After a reset, ask `/api/isalive`: stop if the service is down, record a failure if it's up.** This would tell a service that stopped apart from one that dropped a single request. But a container that restarts (Docker's restart policy, or the JVM killed for memory and brought back) can answer `isalive` a moment later, so the probe would record the file as failed for exactly the outage it was meant to catch.
- **Treat every transport error as unreachable.** A timeout means the service was there and didn't answer in 300 s, which 0029 already handles as the file's fault. Proxy and protocol errors raised on our side don't say the service is down.

## Consequences
- Calling a dropped connection an outage when it was really the file's fault costs a rerun, and the rerun stops at the same file. That would show up at once and could be looked into. The opposite mistake, an outage recorded as failures, stays hidden until someone reads the report or passes `--retry-failed`.
- A PDF that makes GROBID close the connection every time, rather than answer with an error, would stop every run at that file. None of the Seeds does. If one turns up in the full corpus, the fix is to recognise that one case (for example a dropped connection that recurs on the same hash), not to go back to recording outages.
