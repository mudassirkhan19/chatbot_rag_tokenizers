# 0025. The decision judge cuts an abstract only when the model refuses it

- **Date:** 2026-10-18
- **Status:** Accepted. Amends [0021](0021-tev1-decision-model-judge.md).

## Context
Tev1 4B ([0021](0021-tev1-decision-model-judge.md)) takes at most 2,048 tokens of input, and Ollama 0.40.5 never truncates it. A longer input gets HTTP 400 with `prompt 0 has 2748 tokens; expected 1–2048 (input is never truncated)`. The full run (#11) stopped on the 1,926th Candidate, `2023.contents-1.3`, whose "abstract" from Semantic Scholar is 12.7k characters of body text. Some 20 rule passes have a title and abstract over 6,000 characters, most of them the same kind of record: a source that put the paper's text where the abstract goes.

Every cached verdict, the 1,925 Tev1 verdicts saved before the stop and the Audit set's verdicts that chose the threshold, was scored on the whole input. Any fix must leave those inputs exactly as they were, or the cache and the Audit figures would describe a different judge.

## Decision
- **Every Candidate is sent whole first.** Only when Ollama answers 400 with "has N tokens; expected 1–M" does the judge cut the abstract and send it again. It cuts at a word boundary, keeping the share M/N of the abstract with a tenth to spare, and repeats until the model accepts it. The title, the question and the instructions are never cut.
- **The cut is deterministic.** It depends only on the token counts the pinned model reports, so the same Candidate always gets the same cut. The judge prints which Candidate was cut and to how many characters.
- **The question hash doesn't change.** It hashes what the judge is asked ([0007](0007-local-llm-judge.md)), and inputs that fit are asked exactly what they were before, so no cached verdict is invalidated.
- If the title and question alone are too long, the judge stops with an error rather than sending an empty abstract.

## Alternatives considered
- **A fixed character cap on every abstract:** simpler, but where it falls is a guess at characters per token. Any abstract that fit but was longer than the cap would get a different input from the one its cached verdict and the Audit set were scored on.
- **A longer context:** Ollama reports a context length of 2,048 for the loaded model (`/api/ps`). The judge was measured on the Audit set with that setup, and changing how the model runs is a change of judge.
- **Leaving such Candidates `pending`:** a few long records would then stop the manifest from ever being complete, and their first 2,000 tokens say plenty about whether they are about tokenization.
- **Counting tokens first with the model's tokenizer:** that needs the tokenizer outside Ollama, which would be a second pin to keep in step with the served weights.

## Consequences
- The few cut Candidates are judged on the start of their text. Since that text is body text rather than an abstract, the verdict is less certain than usual. The judge lists them in stderr, not in the manifest. In the full run 11 of 7,203 were cut, all venue Editions. 9 are excluded. 2 are included: `10.5281/zenodo.18549852` at P = 0.9955 and `10.5281/zenodo.20615830` at P = 0.8332, both Zenodo records worth checking by hand. The 9 excluded are `2023.contents-1.3`, `10.25144/22349`, `10.67547/fanistiqbollari.2026.724`, `10.1093/nsr/nwae355`, `10.1093/nsr/nwaf004`, `10.5281/zenodo.19238548`, `10.6084/m9.figshare.31859158`, `10.5281/zenodo.19542439` and `10.34778/a48xn206`.
- A cut Candidate costs two or three requests instead of one.
- The test stubs Ollama's 400 answer, with one token per word. The real error text is the one quoted above, from Ollama 0.40.5. A later Ollama that words it differently would bring the 400 back. Upgrading Ollama means re-scoring anyway ([0021](0021-tev1-decision-model-judge.md)).
