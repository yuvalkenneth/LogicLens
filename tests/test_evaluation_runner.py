import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from logiclens.evaluation import (
    _build_prompt,
    _extract_usage,
    _parse_events,
    run_codex_evaluation,
)


ROOT = Path(__file__).parents[1]
CASE = (
    ROOT
    / "evals"
    / "benchmarks"
    / "tiny_python"
    / "repository-understanding.case.json"
)


def test_condition_prompts_do_not_leak_oracle() -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    native, _ = _build_prompt(case, "native")
    logiclens, _ = _build_prompt(case, "logiclens")

    assert "LogicLens is unavailable" in native
    assert ".logiclens/repository-context.json" in logiclens
    assert "build_service constructs" not in native
    assert "build_service constructs" not in logiclens


def test_event_telemetry_uses_last_usage_and_completed_tools() -> None:
    raw = "\n".join(
        [
            '{"type":"item.completed","item":{"type":"reasoning"}}',
            '{"type":"item.completed","item":{"type":"command_execution"}}',
            '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":4}}',
        ]
    )
    assert _extract_usage(_parse_events(raw)) == {
        "input_tokens": 12,
        "output_tokens": 4,
        "cost_usd": None,
        "tool_calls": 1,
        "raw_files_read": None,
    }


def test_dry_run_materializes_isolated_paired_artifacts(tmp_path: Path) -> None:
    fake_codex = tmp_path / "codex"
    fake_codex.write_text("#!/bin/sh\necho 'codex-cli test'\n", encoding="utf-8")
    fake_codex.chmod(0o755)

    session = run_codex_evaluation(
        CASE,
        tmp_path / "results",
        model="test-model",
        repetitions=1,
        seed=4,
        codex_executable=fake_codex,
        dry_run=True,
    )

    manifest = json.loads((session / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["repetitions"] == 1
    assert len(manifest["runs"]) == 2
    assert manifest["completed_runs"] == 0
    assert manifest["failed_runs"] == 2
    results = [
        json.loads((session / path).read_text(encoding="utf-8"))
        for path in manifest["runs"]
    ]
    run_schema = json.loads(
        (ROOT / "evals" / "schemas" / "run-result.schema.json").read_text(
            encoding="utf-8"
        )
    )
    for result in results:
        Draft202012Validator(run_schema).validate(result)
    assert {result["condition"] for result in results} == {"native", "logiclens"}
    assert all(result["status"] == "failed" for result in results)
    native = next(result for result in results if result["condition"] == "native")
    assert native["environment"]["logiclens"] is None
    logiclens = next(result for result in results if result["condition"] == "logiclens")
    assert logiclens["environment"]["logiclens"]["index_wall_ms"] >= 0
    assert json.loads((session / "scoring-packet.blind.json").read_text())["answers"] == []


def test_runner_rejects_changed_fixture(tmp_path: Path) -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    case["repository"]["snapshot_id"] = "0" * 64
    changed_case = ROOT / "evals" / "benchmarks" / "tiny_python" / "changed.case.json"
    try:
        changed_case.write_text(json.dumps(case), encoding="utf-8")
        with pytest.raises(ValueError, match="snapshot"):
            run_codex_evaluation(
                changed_case,
                tmp_path,
                model="test",
                codex_executable=Path("/missing"),
                dry_run=True,
            )
    finally:
        changed_case.unlink(missing_ok=True)
