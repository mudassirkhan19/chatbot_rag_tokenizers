"""Stage 2 of the Relevance verdict: a local open-weight LLM judge and its verdict cache.

The judge reads a Candidate's title and abstract and answers whether the paper makes a
substantive contribution or finding about tokenization. Its verdict is P("Yes"). A chat model
(backends transformers and ollama) gives a softmax over the next-token logits for "Yes" and "No"
only, taken right after the chat template's assistant prefix. A decision model (ollama-decision)
gives the probability it puts on the [judge.decision] true/false question being true. No
threshold is applied here; the manifest builder applies it, so tuning the threshold never means
re-scoring.

Verdicts are cached in the Snapshot together with the model id, its pinned revision and a hash
of what the model was asked: the prompt, or a decision model's question. A cached verdict counts
only while all three still match the config.

torch and transformers are imported only when a Candidate actually needs scoring, so a rerun
from a complete Snapshot never loads them.
"""

import hashlib
import json
import math
import re
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

import httpx

from ..ollama import OLLAMA_URL, Ollama, OllamaModelError, response_json
from .config import JudgeConfig
from .editions import Edition

ANSWERS = ("Yes", "No")

# Ollama's answer when a decision model's input is longer than its context, which it never truncates.
_TOO_LONG = re.compile(r"has (?P<tokens>\d+) tokens; expected 1\u2013(?P<limit>\d+)")


def prompt_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()


def question_hash(config: JudgeConfig) -> str:
    """The hash of what the model is asked: the prompt, or for a decision model its question.

    It covers the config's text, not the request shape built from it: a code change to how either
    is sent needs a new prompt or question to re-score.
    """
    if config.backend == "ollama-decision":
        assert config.decision is not None
        return prompt_hash(json.dumps(asdict(config.decision), sort_keys=True))
    return prompt_hash(config.prompt)


@dataclass(frozen=True)
class JudgeVerdict:
    edition_id: str
    model: str
    revision: str
    prompt_hash: str
    p_yes: float

    def matches(self, config: JudgeConfig) -> bool:
        return (self.model, self.revision, self.prompt_hash) == (config.model, config.revision, question_hash(config))


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


def p_yes_from_logprobs(top_logprobs: Sequence[dict[str, Any]]) -> float:
    """P("Yes"): the softmax over the logprobs of "Yes" and "No" among the top next tokens.

    An answer missing from the list is at most as likely as the last token listed, so it takes
    that logprob. With both missing the score is 0.5, though the model would answer neither.
    """
    logprobs = {entry["token"]: entry["logprob"] for entry in top_logprobs}
    floor = min(logprobs.values())
    yes, no = (logprobs.get(answer, floor) for answer in ANSWERS)
    return 1 / (1 + math.exp(no - yes))


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
        # Hybrid models such as Qwen3-1.7B would think before answering; templates without the
        # switch ignore it.
        chat = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True, enable_thinking=False
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


class _Ollama:
    """A model served by a local Ollama, pinned as ``<digest>@<Ollama version>``: the judge refuses to start
    unless the server runs both (the shared Ollama module, ADRs 0021 and 0054)."""

    def __init__(self, config: JudgeConfig, client: httpx.Client | None = None) -> None:
        self.config = config
        self.ollama = Ollama(client)
        self.client = self.ollama.client
        digest, version = self.ollama.check_pin(config.model, config.revision)
        print(f"judge: using {config.model}@{digest[:12]} from Ollama {version}", file=sys.stderr)

    def _p_yes(self, edition: Edition) -> float:
        raise NotImplementedError

    def score(self, editions: Sequence[Edition]) -> list[float]:
        return [self._p_yes(edition) for edition in editions]


class OllamaJudge(_Ollama):
    """A chat model: the first answer token's logprobs, one prompt at a time, with thinking off so
    the answer comes first."""

    def _p_yes(self, edition: Edition) -> float:
        content = self.config.prompt.format(title=edition.title, abstract=edition.abstract)
        response = self.ollama.chat(
            self.config.model,
            [{"role": "user", "content": content}],
            think=False,
            options={"num_predict": 1, "temperature": 0, "seed": 0},
            logprobs=True,
            top_logprobs=20,
        )
        return p_yes_from_logprobs(response["logprobs"][0]["top_logprobs"])


class OllamaDecisionJudge(_Ollama):
    """A decision model such as Tev1, through Ollama's `/v1/systemone`: P("Yes") is the probability
    it gives that the `[judge.decision]` true/false question is true of the Candidate."""

    def _p_yes(self, edition: Edition) -> float:
        question = self.config.decision
        assert question is not None, "the config requires [judge.decision] for this backend"
        abstract = edition.abstract
        while True:
            response = self.client.post(
                "/v1/systemone",
                json={
                    "model": self.config.model,
                    "state": question.state.format(title=edition.title, abstract=abstract),
                    "questions": {
                        "in_scope": {
                            "type": "noul",
                            "instructions": question.instructions,
                            "criteria": {"true": question.true, "false": question.false},
                        }
                    },
                },
            )
            too_long = _TOO_LONG.search(response.text) if response.status_code == 400 else None
            if too_long is None:
                return float(response_json(response)["answers"]["in_scope"]["noul"])
            abstract = _shorten(abstract, int(too_long["tokens"]), int(too_long["limit"]))
            print(f"judge: {edition.edition_id} is too long for the model; abstract cut to {len(abstract)} characters", file=sys.stderr)


def _shorten(abstract: str, tokens: int, limit: int) -> str:
    """``abstract`` cut at a word boundary, by the share of the input that is over ``limit``, with a
    tenth to spare. Only an input the model refused is ever cut, so every verdict on one that fit
    stays the same.
    """
    keep = int(len(abstract) * limit / tokens * 0.9)
    cut = abstract[:keep].rsplit(" ", 1)[0]
    if not cut or cut == abstract:
        raise OllamaModelError(f"the title and prompt alone are longer than the model's {limit}-token context")
    return cut


def load_judge(config: JudgeConfig) -> Judge:
    if config.backend in ("ollama", "ollama-decision"):
        try:
            return (OllamaJudge if config.backend == "ollama" else OllamaDecisionJudge)(config)
        except httpx.ConnectError as error:
            raise SystemExit(f"judge: no Ollama server at {OLLAMA_URL} ({error}); start it with `ollama serve`") from error
        except OllamaModelError as error:
            raise SystemExit(f"judge: {error}") from error
    try:
        return TransformersJudge(config)
    except ImportError as error:
        raise SystemExit(
            f"judge: {error.name} is not installed. Run `uv sync` to score Candidates, "
            "or pass --no-judge to leave Candidates without a cached verdict pending."
        ) from error
