import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from logiclens.evaluation import (
    _build_prompt,
    _check_answer,
    _codex_answer_schema,
    _extract_usage,
    _install_logiclens_skill,
    _logiclens_invoked,
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


def test_conditions_use_the_same_prompt() -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    prompt, wrapper = _build_prompt(case)

    assert "LogicLens" not in prompt
    assert "build_service constructs" not in prompt
    assert "identical user task" in wrapper


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


def test_logiclens_invocation_is_detected_from_the_tool_trace() -> None:
    events = _parse_events(
        '{"type":"item.completed","item":{"type":"command_execution",'
        '"command":"logiclens map . --db .logiclens/index.sqlite"}}'
    )
    assert _logiclens_invoked(events)
    skill_read = _parse_events(
        '{"type":"item.completed","item":{"type":"command_execution",'
        '"command":"sed -n 1,20p .agents/skills/logiclens/SKILL.md"}}'
    )
    assert not _logiclens_invoked(skill_read)


def test_codex_schema_uses_supported_composition() -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    schema = _codex_answer_schema(ROOT, case)
    encoded = json.dumps(schema)

    assert '"allOf"' not in encoded
    assert '"oneOf"' not in encoded
    assert '"logiclens_ref"' not in encoded
    assert '"uniqueItems"' not in encoded
    assert "evidence.schema.json" not in encoded
    assert schema["properties"]["contract_version"]["type"] == "string"
    assert schema["properties"]["case_id"]["const"] == case["case_id"]
    assert schema["$defs"]["turnAnswer"]["properties"]["turn_id"]["enum"] == [
        "onboarding"
    ]



def test_logiclens_skill_is_added_only_to_the_treatment_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "repository"
    workspace.mkdir()
    _install_logiclens_skill(ROOT, workspace)

    assert (workspace / ".agents" / "skills" / "logiclens" / "SKILL.md").is_file()


def test_strict_claim_evidence_postcondition() -> None:
    case = json.loads(CASE.read_text(encoding="utf-8"))
    answer = {
        "contract_version": "0.1",
        "case_id": case["case_id"],
        "turns": [
            {
                "turn_id": "onboarding",
                "reading_order": [],
                "unknowns": [],
                "claims": [
                    {"stance": "confirmed", "evidence": []},
                ],
            }
        ],
    }

    with pytest.raises(ValueError, match="require evidence"):
        _check_answer(answer, case)


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
    assert logiclens["environment"]["logiclens"]["index_wall_ms"] is None
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
