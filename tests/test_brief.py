import json
from pathlib import Path

from logiclens.brief import validate_repository_brief
from logiclens.database import create_database
from logiclens.inventory import build_inventory
from logiclens.python_modules import analyze_python_modules


ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "tiny_python"
EXAMPLE = ROOT / "evals" / "tiny_python" / "repository-brief.example.json"
EXPECTATIONS = (
    ROOT / "evals" / "tiny_python" / "repository-brief.expectations.json"
)
SCHEMA = ROOT / "src" / "logiclens" / "repository_brief.schema.json"
SKILL_SCHEMA = (
    ROOT / "skills" / "logiclens" / "references" / "repository-brief.schema.json"
)


def mapped_database(tmp_path: Path) -> Path:
    inventory = build_inventory(FIXTURE)
    database = tmp_path / "tiny.sqlite"
    create_database(database, inventory, analyze_python_modules(inventory))
    return database


def test_example_brief_passes_contract_and_expectations(tmp_path: Path) -> None:
    brief = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    expectations = json.loads(EXPECTATIONS.read_text(encoding="utf-8"))

    assert validate_repository_brief(
        brief, mapped_database(tmp_path), expectations
    ) == []


def test_rejects_unknown_evidence_and_confirmed_entry_point(tmp_path: Path) -> None:
    brief = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    brief["purpose"]["evidence"] = ["file:DOES_NOT_EXIST.md"]
    brief["entry_points"] = [
        {
            "target": "module:shop.main",
            "status": "confirmed",
            "reason": "The module is named main.",
            "evidence": ["module:shop.main"],
        }
    ]

    errors = validate_repository_brief(brief, mapped_database(tmp_path))

    assert "unknown evidence reference: file:DOES_NOT_EXIST.md" in errors
    assert any("confirmed entry point lacks deterministic support" in item for item in errors)


def test_repository_brief_schema_is_valid_json() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    assert schema["properties"]["brief_version"] == {"const": "0.1"}
    assert set(schema["required"]) >= {"snapshot_id", "purpose", "unknowns"}
    assert json.loads(SKILL_SCHEMA.read_text(encoding="utf-8")) == schema
