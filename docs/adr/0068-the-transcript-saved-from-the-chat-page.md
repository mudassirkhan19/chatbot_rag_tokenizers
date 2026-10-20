# 0068. The Transcript, saved from the chat page

- **Date:** 2026-10-20
- **Status:** Accepted; the committed Transcript described under Consequences is replaced by [0070](0070-the-chatbot-retrieves-collapsed-and-the-final-chat-numbers.md)'s, asked on the collapsed retriever, and that one by [0077](0077-the-final-chat-run-after-the-text-collapse-the-rewrite-and-per-paper-retrieval.md)'s, asked after #80–#82

## Context
The brief asks for a transcript of one Conversation of at least five Turns, with a follow-up and an unanswerable question. Spec #63 (story 12) and issue #68 ask for it to be a file the page produced, not a copy-paste: a save action that writes the Conversation as Markdown under the reports folder, named by date, with every Turn's question, Rewrite, answer with its markers and reference list. The saved file and the page must render the same Turns from the same records.

## Decision
**`POST /save` renders the records `POST /turn` returned.** The server turns each Turn of its Conversation into the same JSON record the page renders (ADR 0056), and `chat/transcript.py` writes Markdown from those records, so the two never read different fields of a Turn. The wording is written twice, in the page's JavaScript and in the Markdown renderer, and the page tests hold the Markdown to the page's wording for the answer, the references, the invalid markers and the uncited Chunks. Each Turn gets a `## Turn n` heading, then the question, the Rewrite as "Searched as:" on a follow-up, the answer with its markers in place, headed "Answer (Abstention)" when it is one, the reference list in the page's wording, the invalid markers struck through and listed, the retrieved Chunks the answer didn't cite with their anchors, and the timings. The header names the retriever, k and the answer model's pin. The response gives the file's path, and the page shows it.

**The file is `docs/reports/<date>-chat-transcript.md`.** `docs/reports` is where the hand-saved run reports already are. A second save on the same day writes `-2`, `-3` and so on, so no transcript is overwritten. `chat --transcripts` names another folder. A save with no Turn is refused with a 400 and writes nothing.

**The committed transcript is the third Conversation asked, saved as it came.** The developer asked three six-Turn Conversations of the real model (`gemma4:e2b-mlx`, temperature 0) through the page's endpoints and committed the third, the first in which a follow-up resolved and both unanswerable questions were Abstentions. It is not edited. The other two are described under Consequences.

## Alternatives considered
- **Render the transcript from the Turn objects directly.** It's one step shorter, but the page and the file could then drift apart in what they show, and the issue asks for one set of records.
- **Download the transcript in the browser.** The file would land in the user's Downloads, not the repo, and the save response couldn't name a path to commit.
- **One file per Conversation id, or overwriting the day's file.** An id means nothing to a reader. Overwriting loses a transcript saved earlier the same day.
- **Asking Conversations until every Turn is right.** That would make the transcript look better than the bot is. The chat report measures quality; the transcript shows one real Conversation.

## Consequences
- `docs/reports/2026-10-20-chat-transcript.md` has six Turns. Turns 2 and 3 are follow-ups. Turn 2's Rewrite resolves "it" to CANINE. Turn 3's Rewrite only half resolves "that": it describes CANINE's hashing without naming CANINE, retrieves ByT5 Chunks only, and the answer is wrong. It says CANINE processes UTF-8 bytes, which is ByT5's design, and its one Citation is ByT5's introduction. Turn 4 is the Evaluation set's near miss `byt5-learning-rate` (ByT5 states a fine-tuning rate, not a pre-training schedule; see `data/eval/absence-evidence.md`) and Turn 5 (vitamin D) is off topic; both are Abstentions.
- The two Conversations not committed showed three faults that are not in the committed one:
  - "The papers do not answer this question.", a shortened fixed sentence, is not counted as an Abstention by ADR 0064's matcher.
  - "Which learning rate schedule did it use for pre-training?" after a ByT5 question was rewritten to CANINE.
  - "Which country won the 2018 FIFA World Cup?" asked after three Turns of history was answered from a Chunk of 2408.07065v1 about the 2006 World Cup. Asked alone, as `chat-eval` asks it, the bot abstains.
- The transcript holds timings, so a re-save of the same Conversation differs in them. It is a record of one run, not a reproducible report. The chat report is that.
