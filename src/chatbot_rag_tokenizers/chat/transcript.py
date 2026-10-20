"""The Transcript (ADR 0068): the chat page's Conversation saved as Markdown under the reports folder.

It is rendered from the records `POST /turn` returned to the page, so the file and the page show the same Turns:
for each, the question, the Rewrite on a follow-up ("Searched as:"), the answer with its markers, an invalid
marker struck through, the reference list, the retrieved Chunks the answer didn't cite, and the timings. The file
is named by the date it was saved, `<date>-chat-transcript.md`; a later save on the same day takes the next free
`-2`, `-3`, …, so no saved transcript is overwritten.
"""

from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any


def save(records: Sequence[dict[str, Any]], status: dict[str, Any], folder: Path, day: date) -> Path:
    """Writes the Turns' records as a transcript in ``folder`` and returns its path."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{day.isoformat()}-chat-transcript.md"
    copy = 1
    while path.exists():
        copy += 1
        path = folder / f"{day.isoformat()}-chat-transcript-{copy}.md"
    path.write_text(render(records, status, day))
    return path


def render(records: Sequence[dict[str, Any]], status: dict[str, Any], day: date) -> str:
    lines = [
        f"# Chat transcript, {day.isoformat()}",
        "",
        f"Saved from the chat page (`just chat`). Each question retrieved the top {status['k']} Chunks from"
        f" {status['retriever']}, and {status['model']} answered from them.",
    ]
    for number, record in enumerate(records, start=1):
        lines += ["", f"## Turn {number}", "", *_turn(record)]
    return "\n".join(lines) + "\n"


def _turn(record: dict[str, Any]) -> list[str]:
    lines = [f"**Question:** {record['question']}", ""]
    if record["rewrite"] is not None:
        lines += [f"**Searched as:** {record['rewrite']}", ""]
    lines += ["**Answer (Abstention):**" if record["abstention"] else "**Answer:**", "", _answer(record["answer"])]
    if record["references"]:
        lines += ["", "**References:**", ""]
        lines += [f"- [{reference['number']}] {_reference(reference)}" for reference in record["references"]]
    if record["invalid"]:
        markers = " ".join(f"[{number}]" for number in record["invalid"])
        lines += ["", f"Invalid Citations: {markers} name no retrieved Chunk."]
    uncited = [chunk for chunk in record["chunks"] if not chunk["cited"]]
    if uncited:
        lines += ["", "**Retrieved, not cited:**", ""]
        lines += [f"- [{chunk['number']}] {chunk['title']} · {chunk['anchor']}" for chunk in uncited]
    seconds = record["seconds"]
    rewriting = f"rewrite {seconds['rewriting']:.1f} s · " if record["rewrite"] is not None else ""
    lines += ["", f"*{rewriting}retrieval {seconds['retrieval']:.2f} s · answer {seconds['answering']:.1f} s*"]
    return lines


def _answer(parts: Sequence[dict[str, Any]]) -> str:
    """The answer as the page shows it: its text with each marker in place, an invalid one struck through."""
    return "".join(part["text"] if "text" in part else _marker(part) for part in parts).strip()


def _marker(part: dict[str, Any]) -> str:
    return f"[{part['marker']}]" if part["valid"] else f"~~[{part['marker']}]~~"


def _reference(reference: dict[str, Any]) -> str:
    """As the page's reference list writes it: title, Edition, Section and pages."""
    section = " ".join(part for part in (reference["section_number"], reference["section_title"]) if part)
    return f"{reference['title']}. {reference['edition']}, {section}" + (f", {reference['pages']}" if reference["pages"] else "") + "."
