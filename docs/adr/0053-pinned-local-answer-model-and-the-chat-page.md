# 0053. The pinned local answer model, the shared Ollama module and the chat page

- **Date:** 2026-10-19
- **Status:** Accepted. Amends [0021](0021-tev1-decision-model-judge.md) (the judge's Ollama code moves to a shared module).

## Context
Spec #63 asks for a grounded chatbot: a question is answered from retrieved Chunks, with Citations to paper and Section, and the bot says so when the corpus doesn't answer. Issue #64 is its first slice: one question to a cited answer on a local page. It needs an answer model, a way to run it that a reviewer can reproduce, and a page.

The brief asks that the bot run with no API key and no cost. The README's setup is macOS on Apple silicon, and it already requires Ollama 0.40.5 for the judge ([0021](0021-tev1-decision-model-judge.md)). On that runtime, an Ollama upgrade moved the judge's scores by up to 0.16, so Ollama models are pinned as `<digest>@<Ollama version>`.

## Decision
**The answer model is `gemma4:e2b-mlx` on Ollama, pinned as the judge is.** The `[chat]` table of `config/retrieval.toml` holds the model, its pin `e98b54fe1913…@0.40.5`, `think = false` and `temperature = 0.0`. Each request also sends seed 0, as the judge does, so the same question over the same Chunks gets the same text. The model is already pinned in the scope config as an audit comparison model. It is Apache 2.0, 5.2B parameters in nvfp4 (6.5 GB on disk), with a 131k context. On an M1 Max it answers a five-Chunk question in 1 to 2.5 s. `chat` checks the pin when it starts and again after any failure. `just init` checks it and pulls the model when it is missing, as it does for the judge.

**One Ollama module.** The judge's Ollama client, pin parser and digest-plus-version check move to `chatbot_rag_tokenizers/ollama.py`. The judge uses them unchanged: its requests, messages and refusals are the same, and its tests pass as they were. The module adds a chat completion call, which the judge's logprob request and the answer model both use.

**The answer-model boundary is shaped like the embedder's ([0042](0042-dense-baseline-bge-small-behind-the-embedder-boundary.md)).** A protocol has one method, from a list of messages to a text, plus the pin it describes. `load_answer_model` makes the Ollama implementation. The test conftest puts a scripted fake in its place, keyed by text in the last user message, so no test needs Ollama. Any failure to reach Ollama, or a server without the pinned model, becomes one error worded for the person at the page: start Ollama, or run `just init`.

**The retriever is named in `[chat]`.** `retriever` must be one of the retrievers the same file configures, and config loading refuses any other name. It is `dense.bge-small`, the dense baseline, until the embedding comparison (#61) names its choice. `k = 5`, so what the bot sees is what Recall@5 measures.

**The answer step.** The system prompt in `[chat]` fixes the rules. The model answers only from the Chunks, cites each sentence by the Chunk's number in square brackets, and writes the fixed Abstention sentence when the Chunks don't answer. The user message is the question, then the Chunks numbered from 1, each under its context header. The reply is cut into text and markers. A marker naming a retrieved Chunk is a Citation. Any other number is kept and shown as invalid, never dropped. A reply that holds the Abstention sentence is an Abstention, compared word by word after the Passage matcher's normalisation ([0041](0041-passage-matcher-eval-check-and-calibration.md)), so case and punctuation don't matter.

**The page.** `just chat` serves one HTML page on `localhost:8766` with the standard library's threading HTTP server, as `audit label` serves its page, and prints the URL. A Turn shows the answer with its markers and a reference list. Each reference gives the paper's title, the pinned Edition id with its Version, the Section number and title, and the pages. A panel shows the text and Citation anchor of each cited Chunk, with the uncited retrieved Chunks folded away. When Ollama is stopped, runs another version or lacks the model, `chat` still serves the page. It prints the reason in the terminal and shows it on the page, and the next question tries again, so Ollama can be started without restarting `chat`.

## Alternatives considered
- **A hosted API model behind a key**, such as Claude or GPT through an API or OpenRouter. The colleague's research-bot answers this way. It would write better answers and abstain more reliably than a 5B local model. But the brief asks for no key and no cost. A hosted model's weights also change behind its name, so a reviewer could not reproduce the transcript or the chat report. The boundary leaves room for one as a second implementation; none is built.
- **A non-MLX build for CPU-only machines**, such as `gemma4:e2b` in GGUF, which runs on Intel and Linux. The README's setup already needs Apple silicon for MPS, and a GGUF build is another set of weights with another digest. Its answers would differ from the pinned ones, so the transcript and chat report would not reproduce. Offering both would mean two pins and two sets of reported numbers.
- **A larger local model**, such as `gemma4:e4b`. It would answer better, but takes about twice the memory and time. The spec's budget is under 10 GB at chat time with the retriever, and a few seconds per answer.
- **Running the model with transformers in-process.** The judge's history shows Ollama's runtime is what the scores depend on, and Ollama is already a prerequisite. Running in-process would add a second runtime to pin.

## Consequences
- `just init` pulls about 6.5 GB more when the chat model is missing, and stops when Ollama's copy has another digest.
- Changing the answer model, its pin or its settings means editing `[chat]`. The chat report (#63) will print the pin and the prompt's hash.
- A smoke run over the full corpus (BM25, five questions) shows the shape and one weakness. Answers cite Chunks from the right Sections, and an off-topic question abstains. But a near-miss question ("Who won the 2018 football World Cup?") was answered with an unrelated fact from a cited Chunk instead of an Abstention. Rewording the abstention rule did not change it, so the prompt here keeps the simple wording. `chat-eval` (#63) measures abstention on the Evaluation set's unanswerable questions, and its ADR decides any change.
- Duplicate Editions of one Work fill several of the five slots (the WECHSEL v2 preprint and its NAACL Edition both came back) until the Collapsed ranking (#49) wraps the retriever.
- The opt-in test (`RUN_OLLAMA_TESTS=1`) asks the real model a fixture question and gets a valid Citation, the same text twice, and an Abstention on an off-topic question.
