"""Stage 2 of the Relevance verdict: a local open-weight LLM judge and its verdict cache.

The judge reads a Candidate's title and abstract and answers whether the paper makes a
substantive contribution or finding about tokenization. Its verdict is P("Yes"): a softmax over
the next-token logits for "Yes" and "No" only, taken right after the chat template's assistant
prefix. No threshold is applied here; the manifest builder applies it, so tuning the threshold
never means re-scoring.

Verdicts are cached in the Snapshot together with the model id, its pinned revision and a hash
of the prompt. A cached verdict counts only while all three still match the config.

torch and transformers are imported only when a Candidate actually needs scoring, so a rerun
from a complete Snapshot works without them (`uv sync --group judge` installs them).
"""

import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from .config import JudgeConfig
from .editions import Edition

ANSWERS = ("Yes", "No")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


@dataclass(frozen=True)
class JudgeVerdict:
    edition_id: str
    model: str
    revision: str
    prompt_hash: str
    p_yes: float

    def matches(self, config: JudgeConfig) -> bool:
        return (self.model, self.revision, self.prompt_hash) == (config.model, config.revision, prompt_hash(config.prompt))


class VerdictCache:
    """Judge verdicts at ``<snapshot>/verdicts/judge.jsonl``: one JSON line per Edition, sorted by id."""

    def __init__(self, snapshot_root: Path) -> None:
        self.path = snapshot_root / "verdicts" / "judge.jsonl"
        self._verdicts: dict[str, JudgeVerdict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    verdict = JudgeVerdict(**json.loads(line))
                    self._verdicts[verdict.edition_id] = verdict

    def get(self, edition_id: str, config: JudgeConfig) -> JudgeVerdict | None:
        """The cached verdict for ``edition_id``, unless it was made with another model, revision or prompt."""
        verdict = self._verdicts.get(edition_id)
        return verdict if verdict is not None and verdict.matches(config) else None

    def put(self, verdict: JudgeVerdict) -> None:
        self._verdicts[verdict.edition_id] = verdict

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            json.dumps(asdict(self._verdicts[edition_id]), sort_keys=True, separators=(",", ":"))
            for edition_id in sorted(self._verdicts)
        ]
        self.path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")


class Judge(Protocol):
    def score(self, editions: Sequence[Edition]) -> list[float]:
        """P("Yes") for each Edition, in order."""
        ...


class AnswerTokenError(ValueError):
    pass


def answer_token_ids(tokenizer: Any) -> tuple[int, int]:
    """The token ids of "Yes" and "No", which must each be a single token for the model's tokenizer.

    The answer starts a fresh assistant turn, so it is encoded without a leading space.
    """
    ids = []
    for answer in ANSWERS:
        encoded = tokenizer.encode(answer, add_special_tokens=False)
        if len(encoded) != 1:
            raise AnswerTokenError(f"{answer!r} is {len(encoded)} tokens for this tokenizer; the judge needs a single token")
        ids.append(encoded[0])
    if ids[0] == ids[1]:
        raise AnswerTokenError("'Yes' and 'No' encode to the same token")
    return ids[0], ids[1]


class TransformersJudge:
    """Runs the configured model locally with transformers, on MPS or CUDA when available.

    It runs in float32, one prompt at a time. In bf16 the logits are too coarse (P("Yes") lands
    on a few values such as 0.5) and padding a batch changes the scores; on MPS batching is no
    faster either (see ADR 0007).
    """

    def __init__(self, config: JudgeConfig) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._torch = torch
        self.config = config
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        print(f"judge: loading {config.model}@{config.revision} on {self.device}", file=sys.stderr)
        self.tokenizer = AutoTokenizer.from_pretrained(config.model, revision=config.revision)
        self.yes_id, self.no_id = answer_token_ids(self.tokenizer)
        model = AutoModelForCausalLM.from_pretrained(config.model, revision=config.revision, dtype=torch.float32)
        # transformers types .to() as taking a model, not a device.
        self.model = cast(Any, model).to(self.device).eval()

    def _chat(self, edition: Edition) -> str:
        content = self.config.prompt.format(title=edition.title, abstract=edition.abstract)
        chat = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True
        )
        assert isinstance(chat, str)
        return chat

    def _p_yes(self, edition: Edition) -> float:
        torch = self._torch
        # The chat template already adds any special tokens the model expects.
        inputs = self.tokenizer(self._chat(edition), return_tensors="pt", add_special_tokens=False).to(self.device)
        with torch.inference_mode():
            logits = self.model(**inputs).logits[0, -1, :]
        return float(torch.softmax(logits[[self.yes_id, self.no_id]], dim=-1)[0])

    def score(self, editions: Sequence[Edition]) -> list[float]:
        scores = [self._p_yes(edition) for edition in editions]
        if self.device == "mps":
            # Every prompt has its own length, so the MPS allocator keeps caching buffers of new
            # sizes. Kept, they grew by about 1 GB per 50–75 prompts until the system ran out of
            # memory (ADR 0018). Releasing them leaves every score bit-identical.
            self._torch.mps.empty_cache()
        return scores


def load_judge(config: JudgeConfig) -> Judge:
    try:
        return TransformersJudge(config)
    except ImportError as error:
        raise SystemExit(
            f"judge: {error.name} is not installed. Run `uv sync --group judge` to score Candidates, "
            "or pass --no-judge to leave Candidates without a cached verdict pending."
        ) from error
