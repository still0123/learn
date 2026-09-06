from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Protocol

from .models import Score, Task


ALLOWED_SPLITS = {"train", "validation", "test"}
CONVENTIONAL_COMMIT_TYPES = {
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
}
CONVENTIONAL_BRANCH_TYPES = {"feature", "feat", "bugfix", "fix", "hotfix", "release", "chore"}
CONVENTIONAL_BRANCH_TRUNKS = {"main", "master", "develop"}
_COMMIT_HEADER = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9._/-]+)\))?"
    r"(?P<bang>!)?: (?P<description>[^\r\n]+)$"
)


class TaskAdapter(Protocol):
    @property
    def name(self) -> str: ...

    def tasks(self, split: str) -> list[Task]: ...

    def render(self, task: Task) -> str: ...

    def score(self, task: Task, answer: str) -> Score: ...

    def dataset_fingerprint(self) -> str: ...


class ExactMatchJSONLAdapter:
    """Small public adapter for text tasks with exact-match ground truth."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._tasks = self._load()

    @property
    def name(self) -> str:
        return "exact"

    def _load(self) -> list[Task]:
        items: list[Task] = []
        seen: set[str] = set()
        for line_no, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{self.path}:{line_no}: invalid JSON: {exc}") from exc
            task_id = str(item.get("id", "")).strip()
            split = str(item.get("split", "")).strip()
            if not task_id or task_id in seen:
                raise ValueError(f"{self.path}:{line_no}: missing or duplicate task id {task_id!r}")
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", task_id):
                raise ValueError(f"{self.path}:{line_no}: unsafe task id {task_id!r}")
            if split not in ALLOWED_SPLITS:
                raise ValueError(f"{self.path}:{line_no}: invalid split {split!r}")
            if "input" not in item or "expected" not in item:
                raise ValueError(f"{self.path}:{line_no}: input and expected are required")
            seen.add(task_id)
            items.append(Task(
                id=task_id,
                split=split,
                input=str(item["input"]),
                expected=item["expected"],
                metadata=dict(item.get("metadata") or {}),
            ))
        for split in ALLOWED_SPLITS:
            if not any(task.split == split for task in items):
                raise ValueError(f"{self.path}: split {split!r} is empty")
        return items

    def tasks(self, split: str) -> list[Task]:
        if split not in ALLOWED_SPLITS:
            raise ValueError(f"invalid split {split!r}")
        return [task for task in self._tasks if task.split == split]

    def render(self, task: Task) -> str:
        return task.input

    def score(self, task: Task, answer: str) -> Score:
        matched = answer.strip() == str(task.expected).strip()
        return Score(
            value=1.0 if matched else 0.0,
            metrics={"exact_match": 1.0 if matched else 0.0},
            feedback="exact match" if matched else "answer does not exactly match expected output",
        )

    def dataset_fingerprint(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


class JSONValueJSONLAdapter(ExactMatchJSONLAdapter):
    """Scores JSON values semantically while preserving JSON type distinctions."""

    @property
    def name(self) -> str:
        return "json"

    def score(self, task: Task, answer: str) -> Score:
        candidate = _extract_answer(answer)
        try:
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            return Score(
                value=0.0,
                metrics={"valid_json": 0.0, "exact_match": 0.0},
                feedback="answer is not valid JSON",
            )
        try:
            actual = _canonical_json(parsed)
            expected = _canonical_json(task.expected)
        except (TypeError, ValueError):
            return Score(
                value=0.0,
                metrics={"valid_json": 0.0, "exact_match": 0.0},
                feedback="answer contains a non-standard JSON value",
            )
        matched = actual == expected
        return Score(
            value=1.0 if matched else 0.0,
            metrics={"valid_json": 1.0, "exact_match": 1.0 if matched else 0.0},
            feedback="semantic JSON match" if matched else "valid JSON with a different value",
        )


class ConventionalCommitJSONLAdapter(ExactMatchJSONLAdapter):
    """Deterministically scores behavior required by Conventional Commits tasks."""

    @property
    def name(self) -> str:
        return "conventional-commit"

    def _load(self) -> list[Task]:
        tasks = super()._load()
        for task in tasks:
            _validate_commit_expectation(task)
        return tasks

    def score(self, task: Task, answer: str) -> Score:
        expected = task.expected
        text = _extract_commit_answer(answer)
        lines = text.splitlines()
        header = lines[0].strip() if lines else ""
        match = _COMMIT_HEADER.fullmatch(header)
        metric_names = (
            "valid_format",
            "type_match",
            "scope_match",
            "imperative_verb",
            "description_terms",
            "breaking_change",
            "references",
            "body_terms",
        )
        if match is None:
            return Score(
                value=0.0,
                metrics={name: 0.0 for name in metric_names},
                feedback="invalid Conventional Commit header",
            )

        description = match.group("description").strip()
        remainder = "\n".join(lines[1:])
        breaking_footer = re.search(
            r"(?im)^BREAKING CHANGE:\s*(?P<note>.+)$",
            remainder,
        )
        has_command = re.search(r"(?im)^\s*git\s+commit\b", text) is not None
        expected_scope = expected["scope"]
        expected_terms = expected["description_terms"]
        actual_verb = description.split(maxsplit=1)[0].lower() if description else ""

        if expected["breaking"]:
            marker_ok = bool(match.group("bang")) if expected["require_bang"] else bool(
                match.group("bang") or breaking_footer
            )
            note_terms = expected["breaking_note_terms"]
            note_ok = (
                _term_fraction(breaking_footer.group("note"), note_terms)
                if breaking_footer
                else 0.0
            )
            breaking_score = (float(marker_ok) + note_ok) / 2 if note_terms else float(marker_ok)
        else:
            breaking_score = float(not match.group("bang") and breaking_footer is None)

        metrics = {
            "valid_format": float(not has_command),
            "type_match": float(match.group("type") == expected["type"]),
            "scope_match": float(match.group("scope") == expected_scope),
            "imperative_verb": float(actual_verb == expected["verb"]),
            "description_terms": _term_fraction(description, expected_terms),
            "breaking_change": breaking_score,
            "references": _term_fraction(text, expected["references"]),
            "body_terms": _term_fraction(remainder, expected["body_terms"]),
        }
        failed = [name for name, value in metrics.items() if value < 1.0]
        return Score(
            value=sum(metrics.values()) / len(metrics),
            metrics=metrics,
            feedback="all commit assertions passed" if not failed else "failed: " + ", ".join(failed),
        )


class ConventionalBranchJSONLAdapter(ExactMatchJSONLAdapter):
    """Deterministically scores a Conventional Branch name without Git side effects."""

    @property
    def name(self) -> str:
        return "conventional-branch"

    def _load(self) -> list[Task]:
        tasks = super()._load()
        for task in tasks:
            _validate_branch_expectation(task)
        return tasks

    def score(self, task: Task, answer: str) -> Score:
        expected = task.expected
        branch = _extract_branch_answer(answer)
        parsed = _parse_conventional_branch(branch)
        expected_ticket = expected["ticket"]
        description = parsed[1] if parsed else ""
        metrics = {
            "single_branch_output": float(bool(branch) and len(branch.splitlines()) == 1),
            "valid_branch_syntax": float(parsed is not None),
            "type_match": float(parsed is not None and parsed[0] == expected["type"]),
            "description_terms": _term_fraction(
                description.replace("-", " "), expected["description_terms"]
            ),
            "ticket": float(
                (expected_ticket is None and "issue-" not in description)
                or (expected_ticket is not None and f"issue-{expected_ticket}" in description)
            ),
            "exact_branch": float(branch == expected["branch"]),
        }
        failed = [name for name, value in metrics.items() if value < 1.0]
        return Score(
            value=sum(metrics.values()) / len(metrics),
            metrics=metrics,
            feedback="all Conventional Branch assertions passed" if not failed else "failed: " + ", ".join(failed),
        )


class PesterShouldMigrationJSONLAdapter(ExactMatchJSONLAdapter):
    """Scores semantic Pester v5-to-v6 assertion migrations deterministically."""

    @property
    def name(self) -> str:
        return "pester-should-migration"

    def _load(self) -> list[Task]:
        tasks = super()._load()
        for task in tasks:
            _validate_pester_expectation(task)
        return tasks

    def score(self, task: Task, answer: str) -> Score:
        expected = task.expected
        text = _extract_powershell_answer(answer)
        normalized = _normalize_powershell(text)
        metrics = {
            "required_rewrites": _literal_fraction(normalized, expected["required"]),
            "legacy_syntax_removed": float(
                all(_normalize_powershell(item).casefold() not in normalized.casefold()
                    for item in expected["forbidden"])
            ),
            "context_preserved": _literal_fraction(normalized, expected["context"]),
            "code_only_output": float(bool(normalized) and not _contains_explanation(text)),
        }
        failed = [name for name, value in metrics.items() if value < 1.0]
        return Score(
            value=sum(metrics.values()) / len(metrics),
            metrics=metrics,
            feedback="all Pester migration assertions passed" if not failed else "failed: " + ", ".join(failed),
        )


def build_adapter(name: str, path: str | Path) -> TaskAdapter:
    adapters = {
        "conventional-branch": ConventionalBranchJSONLAdapter,
        "conventional-commit": ConventionalCommitJSONLAdapter,
        "exact": ExactMatchJSONLAdapter,
        "json": JSONValueJSONLAdapter,
        "pester-should-migration": PesterShouldMigrationJSONLAdapter,
    }
    try:
        adapter_type = adapters[name]
    except KeyError as exc:
        raise ValueError(f"unknown adapter {name!r}; choose one of {sorted(adapters)}") from exc
    return adapter_type(path)


def _extract_answer(answer: str) -> str:
    text = answer.strip()
    tagged = re.search(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.DOTALL | re.IGNORECASE)
    if tagged:
        text = tagged.group(1).strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    return fenced.group(1).strip() if fenced else text


def _canonical_json(value) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validate_commit_expectation(task: Task) -> None:
    expected = task.expected
    if not isinstance(expected, dict):
        raise ValueError(f"task {task.id}: expected must be an object")
    required = {
        "type",
        "scope",
        "verb",
        "description_terms",
        "breaking",
        "require_bang",
        "breaking_note_terms",
        "references",
        "body_terms",
    }
    if set(expected) != required:
        raise ValueError(f"task {task.id}: expected fields must be {sorted(required)}")
    if expected["type"] not in CONVENTIONAL_COMMIT_TYPES:
        raise ValueError(f"task {task.id}: invalid commit type {expected['type']!r}")
    if expected["scope"] is not None and not re.fullmatch(
        r"[a-z0-9._/-]+", str(expected["scope"])
    ):
        raise ValueError(f"task {task.id}: invalid scope")
    if not isinstance(expected["verb"], str) or not expected["verb"].strip():
        raise ValueError(f"task {task.id}: verb must be a non-empty string")
    for field in ("description_terms", "breaking_note_terms", "references", "body_terms"):
        terms = expected[field]
        if not isinstance(terms, list) or any(
            not isinstance(term, str) or not term.strip() for term in terms
        ):
            raise ValueError(f"task {task.id}: {field} must be a string array")
    if not expected["description_terms"]:
        raise ValueError(f"task {task.id}: description_terms must not be empty")
    if not isinstance(expected["breaking"], bool) or not isinstance(
        expected["require_bang"], bool
    ):
        raise ValueError(f"task {task.id}: breaking flags must be booleans")
    if expected["require_bang"] and not expected["breaking"]:
        raise ValueError(f"task {task.id}: require_bang needs breaking=true")


def _validate_branch_expectation(task: Task) -> None:
    expected = task.expected
    if not isinstance(expected, dict):
        raise ValueError(f"task {task.id}: expected must be an object")
    required = {"branch", "type", "ticket", "description_terms"}
    if set(expected) != required:
        raise ValueError(f"task {task.id}: expected fields must be {sorted(required)}")
    branch = expected["branch"]
    if not isinstance(branch, str) or _parse_conventional_branch(branch) is None:
        raise ValueError(f"task {task.id}: expected branch is not Conventional Branch syntax")
    parsed = _parse_conventional_branch(branch)
    if expected["type"] != parsed[0]:
        raise ValueError(f"task {task.id}: expected type does not match expected branch")
    if expected["ticket"] is not None and not re.fullmatch(r"[0-9]+", str(expected["ticket"])):
        raise ValueError(f"task {task.id}: ticket must be digits or null")
    terms = expected["description_terms"]
    if not isinstance(terms, list) or not terms or any(
        not isinstance(term, str) or not re.fullmatch(r"[a-z0-9]+", term) for term in terms
    ):
        raise ValueError(f"task {task.id}: description_terms must be a non-empty lowercase token array")


def _extract_branch_answer(answer: str) -> str:
    text = answer.strip()
    tagged = re.fullmatch(r"<answer>\s*(.*?)\s*</answer>", text, flags=re.DOTALL | re.IGNORECASE)
    if tagged:
        text = tagged.group(1).strip()
    fenced = re.fullmatch(r"```(?:text|plaintext)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    return (fenced.group(1) if fenced else text).strip()


def _parse_conventional_branch(branch: str) -> tuple[str, str] | None:
    if branch in CONVENTIONAL_BRANCH_TRUNKS:
        return "trunk", branch
    if branch.count("/") != 1:
        return None
    branch_type, description = branch.split("/", 1)
    if branch_type not in CONVENTIONAL_BRANCH_TYPES or not description:
        return None
    if not re.fullmatch(r"[a-z0-9.-]+", description):
        return None
    if description[0] in "-." or description[-1] in "-.":
        return None
    if any(token in description for token in ("--", "..", "-.", ".-")):
        return None
    if branch_type != "release" and "." in description:
        return None
    return branch_type, description


def _extract_commit_answer(answer: str) -> str:
    text = answer.strip()
    tagged = re.fullmatch(
        r"<answer>\s*(.*?)\s*</answer>",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if tagged:
        text = tagged.group(1).strip()
    fenced = re.fullmatch(
        r"```(?:text|plaintext)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return fenced.group(1).strip() if fenced else text


def _term_fraction(text: str, terms: list[str]) -> float:
    if not terms:
        return 1.0
    return sum(_contains_term(text, term) for term in terms) / len(terms)


def _contains_term(text: str, term: str) -> bool:
    if re.fullmatch(r"[A-Za-z0-9_-]+", term):
        return re.search(rf"(?<![\w-]){re.escape(term)}(?![\w-])", text, re.IGNORECASE) is not None
    return term.casefold() in text.casefold()


def _validate_pester_expectation(task: Task) -> None:
    expected = task.expected
    if not isinstance(expected, dict) or set(expected) != {"required", "forbidden", "context"}:
        raise ValueError(
            f"task {task.id}: Pester expected fields must be required, forbidden, context"
        )
    for field in ("required", "forbidden", "context"):
        values = expected[field]
        if not isinstance(values, list) or not values or any(
            not isinstance(value, str) or not value.strip() for value in values
        ):
            raise ValueError(f"task {task.id}: {field} must be a non-empty string array")


def _extract_powershell_answer(answer: str) -> str:
    text = answer.strip()
    tagged = re.fullmatch(
        r"<answer>\s*(.*?)\s*</answer>",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if tagged:
        text = tagged.group(1).strip()
    fenced = re.fullmatch(
        r"```(?:powershell|pwsh|ps1|text|plaintext)?\s*(.*?)\s*```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return fenced.group(1).strip() if fenced else text


def _normalize_powershell(text: str) -> str:
    return "\n".join(
        re.sub(r"[\t ]+", " ", line).strip()
        for line in text.replace("\r\n", "\n").split("\n")
        if line.strip()
    )


def _literal_fraction(text: str, expected: list[str]) -> float:
    normalized = text.casefold()
    return sum(
        _normalize_powershell(item).casefold() in normalized
        for item in expected
    ) / len(expected)


def _contains_explanation(text: str) -> bool:
    return re.search(
        r"(?im)^\s*(?:here(?:'s| is)|migrated(?: code)?\s*:|output\s*:|explanation\s*:|"
        r"the migrated)\b",
        text,
    ) is not None
