# 0001. Python 3.12, managed with uv

- **Date:** 2026-10-15
- **Status:** Accepted

## Context
The project is a Python RAG pipeline that will depend on the ML stack (PyTorch, sentence-transformers, possibly FAISS) plus PDF parsing libraries. The local system Python is 3.14. Reviewers must be able to reproduce the environment from the README in a few commands.

## Decision
- Target **Python 3.12** (`requires-python = ">=3.12"`, pinned in `.python-version`).
- Use **uv** for the virtual environment, dependency resolution and the lockfile (`uv.lock` is committed).
- Use the `src/` package layout (`src/chatbot_rag_tokenizers/`).

## Alternatives considered
- **Python 3.14 (system default):** newest, but prebuilt wheels for torch, faiss and some PDF parsers lag behind new Python releases, which risks source builds or missing packages.
- **Python 3.13:** better supported than 3.14, but 3.12 is still the most widely supported version across the ML ecosystem.
- **pip + venv / Poetry:** work, but uv is faster, produces a cross-platform lockfile and can download the pinned interpreter itself, so `uv sync` is the only setup step.

## Consequences
- Setup for reviewers is `uv sync`; uv fetches Python 3.12 if it isn't installed.
- We can't use 3.13+ language features, which we don't need.
