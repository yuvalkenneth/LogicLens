"""Minimal paired Codex evaluation runner."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import metadata
import json
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import time
from typing import Any, Sequence
from uuid import uuid4

from logiclens.database import create_database, read_repository_brief_context
from logiclens.inventory import build_inventory
from logiclens.python_modules import analyze_python_modules


ADAPTER_ID = "codex-cli"
ADAPTER_VERSION = "0.1"


def run_codex_evaluation(
    case_path: Path,
    results_directory: Path,
    *,
    model: str,
    repetitions: int | None = None,
    seed: int = 0,
    codex_executable: Path | None = None,
    dry_run: bool = False,
) -> Path:
    """Run a randomized native/LogicLens comparison and return its session path."""
    case_path = case_path.resolve()
    root = _project_root(case_path)
    case = _read_json(case_path)
    _check_case(case, root)
    executable, harness_version = _resolve_codex(codex_executable)

    count = repetitions or case["protocol"]["repetitions"]
    if count < 1:
        raise ValueError("repetitions must be at least 1")
    conditions = [item["condition_id"] for item in case["protocol"]["conditions"]]
    schedule = [
        (condition, repetition)
        for repetition in range(1, count + 1)
        for condition in conditions
    ]
    if case["protocol"]["randomize_condition_order"]:
        random.Random(seed).shuffle(schedule)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session = results_directory.resolve() / (
        f"{case['case_id']}-{timestamp}-{uuid4().hex[:6]}"
    )
    session.mkdir(parents=True, exist_ok=False)
    output_schema = _codex_answer_schema(root, case)
    schema_path = session / "answer.schema.json"
    _write_json(schema_path, output_schema)

    run_paths: list[str] = []
    statuses: list[str] = []
    blind_items: list[dict[str, Any]] = []
    blind_key: list[dict[str, Any]] = []
    for sequence_index, (condition, repetition) in enumerate(schedule, start=1):
        run_result = _run_once(
            root=root,
            case=case,
            condition=condition,
            repetition=repetition,
            sequence_index=sequence_index,
            executable=executable,
            harness_version=harness_version,
            model=model,
            output_schema=schema_path,
            session=session,
            dry_run=dry_run,
        )
        relative_result = f"runs/{run_result['run_id']}/run-result.json"
        run_paths.append(relative_result)
        statuses.append(run_result["status"])
        if run_result["output"] is not None:
            blind_id = f"answer-{uuid4().hex[:12]}"
            blind_items.append(
                {"blind_id": blind_id, "answer": run_result["output"]["value"]}
            )
            blind_key.append(
                {
                    "blind_id": blind_id,
                    "run_id": run_result["run_id"],
                    "condition": condition,
                    "repetition": repetition,
                }
            )

    manifest = {
        "contract_version": "0.1",
        "case_id": case["case_id"],
        "seed": seed,
        "model": model,
        "repetitions": count,
        "dry_run": dry_run,
        "completed_runs": statuses.count("completed"),
        "failed_runs": len(statuses) - statuses.count("completed"),
        "runs": run_paths,
    }
    _write_json(session / "manifest.json", manifest)
    _write_json(session / "scoring-packet.blind.json", {"answers": blind_items})
    _write_json(session / "scoring-key.private.json", {"answers": blind_key})
    return session


def _run_once(
    *,
    root: Path,
    case: dict[str, Any],
    condition: str,
    repetition: int,
    sequence_index: int,
    executable: Path,
    harness_version: str | None,
    model: str,
    output_schema: Path,
    session: Path,
    dry_run: bool,
) -> dict[str, Any]:
    run_id = f"{condition}-r{repetition}-{uuid4().hex[:8]}"
    run_directory = session / "runs" / run_id
    run_directory.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    started_clock = time.monotonic()
    fixture = root / case["repository"]["fixture_path"]
    logiclens_environment = None

    with tempfile.TemporaryDirectory(prefix="logiclens-eval-") as temporary:
        workspace = Path(temporary) / "repository"
        shutil.copytree(fixture, workspace)
        index_wall_ms = 0
        if condition == "logiclens":
            index_started = time.monotonic()
            inventory = build_inventory(workspace)
            database = workspace / ".logiclens" / "index.sqlite"
            create_database(database, inventory, analyze_python_modules(inventory))
            context = read_repository_brief_context(database)
            _write_json(workspace / ".logiclens" / "repository-context.json", context)
            index_wall_ms = round((time.monotonic() - index_started) * 1000)
            logiclens_environment = {
                "commit": _git_commit(root),
                "version": _logiclens_version(),
                "index_wall_ms": index_wall_ms,
            }

        prompt, wrapper = _build_prompt(case, condition)
        prompt_path = run_directory / "prompt.txt"
        prompt_path.write_text(prompt, encoding="utf-8")
        raw_path = run_directory / "events.jsonl"
        final_path = run_directory / "answer.json"
        stderr_path = run_directory / "stderr.txt"
        command = [
            str(executable),
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--json",
            "--model",
            model,
            "--output-schema",
            str(output_schema),
            "--output-last-message",
            str(final_path),
            "--cd",
            str(workspace),
            "-",
        ]

        status = "completed"
        error = None
        events: list[dict[str, Any]] = []
        answer = None
        if dry_run:
            status = "failed"
            error = "dry run: Codex was not invoked"
            stderr_path.write_text("", encoding="utf-8")
            raw_path.write_text("", encoding="utf-8")
        else:
            try:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    capture_output=True,
                    timeout=case["protocol"]["budget"]["wall_seconds"],
                    check=False,
                )
                raw_path.write_text(completed.stdout, encoding="utf-8")
                stderr_path.write_text(completed.stderr, encoding="utf-8")
                events = _parse_events(completed.stdout)
                if completed.returncode != 0:
                    status = "failed"
                    error = f"Codex exited with status {completed.returncode}"
                else:
                    answer = _read_json(final_path)
                    _check_answer(answer, case)
            except subprocess.TimeoutExpired as exc:
                status = "timed_out"
                error = f"Codex exceeded {exc.timeout} seconds"
                raw_path.write_text(exc.stdout or "", encoding="utf-8")
                stderr_path.write_text(exc.stderr or "", encoding="utf-8")
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                status = "failed"
                error = str(exc)

    usage = _extract_usage(events)
    result = {
        "contract_version": "0.1",
        "run_id": run_id,
        "case_id": case["case_id"],
        "track": "controlled_model",
        "condition": condition,
        "repetition": repetition,
        "sequence_index": sequence_index,
        "harness": {
            "adapter_id": ADAPTER_ID,
            "adapter_version": ADAPTER_VERSION,
            "name": "Codex CLI",
            "version": harness_version,
        },
        "model": {
            "provider": "openai",
            "name": model,
            "version": None,
            "configuration": {},
        },
        "environment": {
            "repository_snapshot_id": case["repository"]["snapshot_id"],
            "network_access": False,
            "history_access": False,
            "clean_workspace": True,
            "prompt_wrapper": wrapper,
            "logiclens": logiclens_environment,
        },
        "timing": {
            "started_at": started.isoformat(),
            "wall_ms": round((time.monotonic() - started_clock) * 1000),
        },
        "usage": usage,
        "status": status,
        "output": None
        if answer is None
        else {
            "schema": case["agent_input"]["output_schema"],
            "value": answer,
            "raw_output_path": f"runs/{run_id}/answer.json",
        },
        "artifacts": [
            f"runs/{run_id}/prompt.txt",
            f"runs/{run_id}/events.jsonl",
            f"runs/{run_id}/stderr.txt",
        ],
        "error": error,
    }
    _write_json(run_directory / "run-result.json", result)
    return result


def _build_prompt(case: dict[str, Any], condition: str) -> tuple[str, str]:
    condition_data = next(
        item
        for item in case["protocol"]["conditions"]
        if item["condition_id"] == condition
    )
    if condition == "logiclens":
        method = (
            "Begin with .logiclens/repository-context.json, which contains a deterministic "
            "LogicLens file/module/import/symbol map. Treat it as the primary evidence map. "
            "Then make only targeted source reads needed to confirm behavior. LogicLens "
            "references use IDs from that context; source spans use repository-relative paths."
        )
    else:
        method = (
            "LogicLens is unavailable. Use the coding harness's normal local "
            "repository tools."
        )
    wrapper = (
        "Fresh snapshot; no network or repository history; condition-specific investigation; "
        "JSON answer constrained by the case output schema."
    )
    turns = "\n\n".join(
        f"Turn {turn['turn_id']}: {turn['prompt']}"
        for turn in case["agent_input"]["turns"]
    )
    prompt = f"""You are evaluating repository understanding on the current snapshot.

Rules:
- Do not use the network, Git history, or files outside the current workspace.
- Do not modify the workspace.
- Do not invent missing behavior. Separate confirmed facts, inferences, and unknowns.
- Cite exact source spans for source claims. A source span uses 1-based line numbers.
- Return only JSON matching the supplied output schema.
- Set contract_version to \"0.1\" and case_id to \"{case['case_id']}\".

Investigation method:
{method}
{condition_data.get('instructions', '')}

Task:
{turns}
"""
    return prompt, wrapper


def _extract_usage(events: Sequence[dict[str, Any]]) -> dict[str, Any]:
    input_tokens = output_tokens = None
    tool_calls = 0
    for event in events:
        usage = event.get("usage")
        if isinstance(usage, dict):
            input_tokens = usage.get("input_tokens", input_tokens)
            output_tokens = usage.get("output_tokens", output_tokens)
        if event.get("type") == "item.completed" and isinstance(
            event.get("item"), dict
        ):
            if event["item"].get("type") not in {"agent_message", "reasoning"}:
                tool_calls += 1
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": None,
        "tool_calls": tool_calls,
        "raw_files_read": None,
    }


def _parse_events(raw: str) -> list[dict[str, Any]]:
    events = []
    for line in raw.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    return events


def _resolve_codex(explicit: Path | None) -> tuple[Path, str | None]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit.expanduser())
    elif located := shutil.which("codex"):
        candidates.append(Path(located))
    if explicit is None:
        candidates.extend(
            sorted(
                Path.home().glob(".nvm/versions/node/*/bin/codex"), reverse=True
            )
        )
        candidates.append(Path("/Applications/ChatGPT.app/Contents/Resources/codex"))
    for candidate in dict.fromkeys(path.resolve() for path in candidates):
        if not candidate.is_file():
            continue
        try:
            result = subprocess.run(
                [str(candidate), "--version"],
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            version = (result.stdout or result.stderr).strip() or None
            return candidate, version
    raise FileNotFoundError("No working Codex CLI found; pass --codex with its path")


def _codex_answer_schema(root: Path, case: dict[str, Any]) -> dict[str, Any]:
    schema = _read_json(root / case["agent_input"]["output_schema"])
    evidence = _read_json(root / "evals" / "schemas" / "evidence.schema.json")

    def replace(value: Any) -> Any:
        if isinstance(value, dict):
            if value.get("$ref", "").endswith("/evidence.schema.json"):
                return replace(evidence)
            converted = {
                ("anyOf" if key == "oneOf" else key): replace(item)
                for key, item in value.items()
                if key not in {"$schema", "$id", "allOf"}
            }
            if "const" in converted and "type" not in converted:
                converted["type"] = _json_type(converted["const"])
            return converted
        if isinstance(value, list):
            return [replace(item) for item in value]
        return value

    return replace(schema)


def _json_type(value: Any) -> str:
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if value is None:
        return "null"
    raise ValueError(f"unsupported JSON const type: {type(value).__name__}")


def _check_case(case: dict[str, Any], root: Path) -> None:
    if case.get("target", {}).get("kind") != "end_to_end":
        raise ValueError("Codex paired runs require an end_to_end case")
    conditions = {item["condition_id"] for item in case["protocol"]["conditions"]}
    if conditions != {"native", "logiclens"}:
        raise ValueError("case must define native and logiclens conditions")
    fixture = root / case["repository"]["fixture_path"]
    inventory = build_inventory(fixture)
    if inventory.snapshot_hash != case["repository"]["snapshot_id"]:
        raise ValueError("fixture does not match the case snapshot")


def _check_answer(answer: Any, case: dict[str, Any]) -> None:
    if not isinstance(answer, dict):
        raise ValueError("Codex answer is not a JSON object")
    if answer.get("contract_version") != "0.1" or answer.get("case_id") != case[
        "case_id"
    ]:
        raise ValueError("Codex answer does not identify this evaluation case")
    expected_turns = {item["turn_id"] for item in case["agent_input"]["turns"]}
    actual_turns = {
        item.get("turn_id")
        for item in answer.get("turns", [])
        if isinstance(item, dict)
    }
    if actual_turns != expected_turns:
        raise ValueError("Codex answer does not contain exactly the requested turns")
    for turn in answer["turns"]:
        for claim in turn["claims"]:
            if claim["stance"] in {"confirmed", "inferred"} and not claim["evidence"]:
                raise ValueError("confirmed and inferred claims require evidence")


def _project_root(path: Path) -> Path:
    for parent in (path.parent, *path.parents):
        if (parent / "pyproject.toml").is_file() and (parent / "evals").is_dir():
            return parent
    raise ValueError(f"cannot find LogicLens project root for {path}")


def _git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _logiclens_version() -> str:
    try:
        return metadata.version("logiclens")
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
