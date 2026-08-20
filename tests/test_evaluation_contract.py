import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
import pytest
from referencing import Registry, Resource

from logiclens.database import create_database, read_repository_brief_context
from logiclens.inventory import build_inventory
from logiclens.python_modules import analyze_python_modules


ROOT = Path(__file__).parents[1]
SCHEMA_DIR = ROOT / "evals" / "schemas"
CASE_DIR = ROOT / "evals" / "benchmarks" / "tiny_python"
EXAMPLE_DIR = ROOT / "evals" / "examples"


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMAS = {path.name: _load(path) for path in SCHEMA_DIR.glob("*.json")}
REGISTRY = Registry().with_resources(
    (schema["$id"], Resource.from_contents(schema)) for schema in SCHEMAS.values()
)


def _validate(schema_name: str, data: object) -> None:
    Draft202012Validator(
        SCHEMAS[schema_name],
        registry=REGISTRY,
        format_checker=FormatChecker(),
    ).validate(data)


def test_schemas_and_examples_are_valid() -> None:
    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)

    answer = _load(EXAMPLE_DIR / "answer.example.json")
    run = _load(EXAMPLE_DIR / "run-result.example.json")
    _validate("answer.schema.json", answer)
    _validate("run-result.schema.json", run)
    _validate("answer.schema.json", run["output"]["value"])
    _validate(
        "score-result.schema.json",
        _load(EXAMPLE_DIR / "score-result.example.json"),
    )
    _validate(
        "comparison-result.schema.json",
        _load(EXAMPLE_DIR / "comparison-result.example.json"),
    )
    _validate(
        "harness-adapter.schema.json",
        _load(EXAMPLE_DIR / "harness-adapter.example.json"),
    )


def test_tiny_python_cases_are_reproducible(tmp_path: Path) -> None:
    fixture = ROOT / "tests" / "fixtures" / "tiny_python"
    inventory = build_inventory(fixture)
    cases = [_load(path) for path in sorted(CASE_DIR.glob("*.case.json"))]

    for case in cases:
        _validate("eval-case.schema.json", case)
        assert case["repository"]["snapshot_id"] == inventory.snapshot_hash

        turn_ids = {turn["turn_id"] for turn in case["agent_input"]["turns"]}
        assert len(turn_ids) == len(case["agent_input"]["turns"])
        assert (ROOT / case["agent_input"]["output_schema"]).is_file()
        for artifact in case["agent_input"]["artifacts"]:
            assert (ROOT / artifact).is_file()
        for fact in case["oracle"]["facts"]:
            assert set(fact["applies_to_turns"]) <= turn_ids
            _check_source_evidence(fixture, fact["evidence"])
        for unknown in case["oracle"]["expected_unknowns"]:
            assert set(unknown["applies_to_turns"]) <= turn_ids
        if relation_path := case["oracle"].get("relation_oracle_path"):
            assert (ROOT / relation_path).is_file()

        criteria = case["oracle"]["success_criteria"]
        fact_ids = [item["fact_id"] for item in case["oracle"]["facts"]]
        unknown_ids = [
            item["unknown_id"] for item in case["oracle"]["expected_unknowns"]
        ]
        decision_ids = [
            item["subject_id"] for item in case["oracle"]["expected_decisions"]
        ]
        assert len(set(fact_ids)) == len(fact_ids)
        assert len(set(unknown_ids)) == len(unknown_ids)
        assert len(set(decision_ids)) == len(decision_ids)
        assert sum(item["weight"] for item in criteria) == pytest.approx(1.0)
        assert len({item["criterion_id"] for item in criteria}) == len(criteria)
        oracle_ids = {
            *fact_ids,
            *unknown_ids,
            *decision_ids,
        }
        for criterion in criteria:
            assert set(criterion["oracle_ids"]) <= oracle_ids

        if case["target"]["kind"] == "end_to_end":
            conditions = {
                condition["condition_id"]: condition["logiclens_enabled"]
                for condition in case["protocol"]["conditions"]
            }
            assert len(case["protocol"]["conditions"]) == 2
            assert conditions == {"native": False, "logiclens": True}
            assert case["protocol"]["count_indexing_cost"] is True
        else:
            assert (ROOT / case["target"]["role_definition"]).is_file()

    context_path = CASE_DIR / "inputs" / "repository-brief-context.json"
    database = tmp_path / "tiny.sqlite"
    create_database(database, inventory, analyze_python_modules(inventory))
    assert _load(context_path) == read_repository_brief_context(database)


def test_comparison_example_is_paired() -> None:
    comparison = _load(EXAMPLE_DIR / "comparison-result.example.json")
    assert len(comparison["native_run_ids"]) == comparison["repetitions"]
    assert len(comparison["logiclens_run_ids"]) == comparison["repetitions"]
    for metric in comparison["metrics"].values():
        assert metric["paired_delta"] == (
            metric["logiclens_mean"] - metric["native_mean"]
        )
        interval = metric["confidence_interval_95"]
        assert interval["lower"] <= metric["paired_delta"] <= interval["upper"]


def test_contract_rejects_leaky_or_unsupported_results() -> None:
    answer = _load(EXAMPLE_DIR / "answer.example.json")
    answer["turns"][0]["claims"][0]["evidence"] = []
    with pytest.raises(ValidationError):
        _validate("answer.schema.json", answer)

    run = _load(EXAMPLE_DIR / "run-result.example.json")
    run["environment"]["logiclens"] = {
        "commit": "example",
        "version": "0.0.0",
        "index_wall_ms": 1,
    }
    with pytest.raises(ValidationError):
        _validate("run-result.schema.json", run)

    role_case = _load(CASE_DIR / "repository-classifier.case.json")
    del role_case["target"]["role_definition"]
    with pytest.raises(ValidationError):
        _validate("eval-case.schema.json", role_case)


def test_score_example_uses_the_case_rubric() -> None:
    case = _load(CASE_DIR / "repository-understanding.case.json")
    score = _load(EXAMPLE_DIR / "score-result.example.json")
    weights = {
        item["criterion_id"]: item["weight"]
        for item in case["oracle"]["success_criteria"]
    }
    values = {
        item["criterion_id"]: item["value"]
        for item in score["criterion_judgments"]
    }
    assert values.keys() == weights.keys()
    assert score["metrics"]["task_success"] == pytest.approx(
        sum(weights[key] * values[key] for key in weights)
    )


def _check_source_evidence(fixture: Path, evidence_items: list[dict]) -> None:
    context = _load(CASE_DIR / "inputs" / "repository-brief-context.json")
    references = {
        *(f"file:{item['path']}" for item in context["files"]),
        *(f"module:{item['name']}" for item in context["modules"]),
        *(item["id"] for item in context["symbols"]),
        *(
            f"import:{item['source']}->{item['target']}"
            for item in context["imports"]
            if item["target"]
        ),
    }
    for evidence in evidence_items:
        if evidence["kind"] == "logiclens_ref":
            assert evidence["reference"] in references
            continue
        source = fixture / evidence["path"]
        assert source.is_file()
        line_count = len(source.read_text(encoding="utf-8").splitlines())
        assert 1 <= evidence["start_line"] <= evidence["end_line"] <= line_count
