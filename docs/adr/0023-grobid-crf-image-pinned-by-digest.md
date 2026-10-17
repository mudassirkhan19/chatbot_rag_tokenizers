# 0023. GROBID's CRF image, pinned by digest in config/parse.toml

- **Date:** 2026-10-17
- **Status:** Accepted

## Context
The parse step to come (#14) will send each pinned PDF to a GROBID service, and its output must be reproducible: its cache will be keyed by parser version and its report will name the image. A Docker tag can be re-pushed, so a tag alone does not fix what runs. `just init`, `just grobid-up` and the parse step all need the same image, and the setup has to work on the author's Apple silicon Mac.

GROBID publishes two images per release on Docker Hub (`grobid/grobid`). The **full** image (`<version>-full`, about 8 GB) adds deep-learning models for references, affiliations, header and funding; it is built for amd64 only and runs on Apple silicon only under emulation. The **CRF** image (`<version>-crf`, about 500 MB) uses only the CRF models and has a native arm64 build. GROBID's own docs recommend the CRF image when only full text is needed, for RAG and search preprocessing.

## Decision
- **Image:** `grobid/grobid:0.9.1-crf`, the latest release (August 2026), pinned to its multi-arch index digest `sha256:223957791ac2bbe48609dcc58a689b16b60baeae13a8734ef440ae6bfb38f4cd`. The digest was read from the registry (`Docker-Content-Digest` of `/v2/grobid/grobid/manifests/0.9.1-crf`), and the index holds linux/amd64 and linux/arm64 images, so Docker runs the native one on either machine.
- **One place:** `[grobid]` in `config/parse.toml` holds `image`, `tag`, `digest` and `port`. The parse step's own settings will join this file in #14. `chatbot_rag_tokenizers.parsing.config` loads it and checks every field's type and the digest's form. `chatbot_rag_tokenizers.parsing.grobid_env` prints the image reference, tag, port and service URL as shell assignments for the justfile, so the recipes never parse TOML themselves and never build the URL a second time.
- **Docker uses the digest only** (`grobid/grobid@sha256:…`). The tag is a readable label for messages and reports.
- **Recipes:** `just init` pulls the image unless it is already present. `just grobid-up [timeout]` starts a container named `chatbot-rag-tokenizers-grobid`, with `--init --ulimit core=0` as GROBID's docs advise, publishes it on `127.0.0.1` only (port 8070 by default), so GROBID is not reachable from the network, and waits until `/api/isalive` answers `true`, failing after 180 s by default with a message pointing to `docker logs`. A running container from the pinned image on the configured port is left alone; a stopped one, or one from an older pin or another port, is replaced. `just grobid-down` removes the container, or says it is not running.

## Alternatives considered
- **The full image.** Better reference and citation-context parsing, by a few F1 points per GROBID's docs, but amd64 only. Under emulation it is much slower, and its TensorFlow models may not run at all. Its bibliography gain matters little here: the chunks #14 builds will come from body text, and the bibliography is only an input to the later dedup stage. The parser spike (#17) can revisit this.
- **A tag without a digest.** Simple, but a re-pushed tag would change the parser without any change in the repo.
- **The pin in `config/scope.toml`.** That file is the collection scope; parsing settings would be unrelated to it.
- **The pin in the justfile, or in `pyproject.toml`.** `parse` would have to read the justfile, and `pyproject.toml` holds packaging and tool settings, not pipeline config.
- **docker compose.** One more file and tool for a single container; two short recipes cover start, wait and stop.

## Consequences
- Every machine runs the same GROBID bytes, and the parse report can name the exact digest.
- Upgrading GROBID is a two-line change in `config/parse.toml` (tag and digest), which will also invalidate the parse cache once #14 keys it by the digest.
- The recipes are tested with a fake `docker`, `curl` and `uv` on PATH (`tests/test_dev_setup.py`); a real container start is checked by hand in the #13 checklist.
- Docker Desktop's default memory may be too low for full-text parsing; GROBID's docs suggest about 4 GB.
