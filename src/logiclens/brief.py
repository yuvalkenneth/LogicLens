"""Repository Brief contract and deterministic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from logiclens.database import read_repository_brief_context


Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Evidence = Annotated[list[Text], Field(min_length=1)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Purpose(StrictModel):
    summary: Text
    evidence: Evidence
    confidence: float = Field(ge=0, le=1)


class Technology(StrictModel):
    name: Text
    role: Text
    evidence: Evidence


class Component(StrictModel):
    name: Text
    members: Annotated[list[Text], Field(min_length=1)]
    reason: Text
    evidence: Evidence


class EntryPoint(StrictModel):
    target: Text
    status: Literal["candidate", "confirmed"]
    reason: Text
    evidence: Evidence


class Flow(StrictModel):
    name: Text
    steps: Annotated[list[Text], Field(min_length=1)]
    reason: Text
    evidence: Evidence


class ReadingItem(StrictModel):
    target: Text
    reason: Text


class RepositoryBrief(StrictModel):
    brief_version: Literal["0.1"]
    snapshot_id: Text
    purpose: Purpose
    technologies: list[Technology]
    components: list[Component]
    entry_points: list[EntryPoint]
    flows: list[Flow]
    reading_order: list[ReadingItem]
    unknowns: list[Text]


class BriefExpectations(StrictModel):
    purpose_terms: list[Text] = []
    technology_names: list[Text] = []
    required_component_member_groups: list[list[Text]] = []
    maximum_confirmed_entry_points: int | None = Field(default=None, ge=0)
    maximum_flows: int | None = Field(default=None, ge=0)
    required_unknown_terms: list[Text] = []


def validate_repository_brief(
    data: object,
    database_path: Path,
    expectation_data: object | None = None,
) -> list[str]:
    try:
        brief = RepositoryBrief.model_validate(data)
    except ValidationError as error:
        return [
            f"schema:{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        ]

    context = read_repository_brief_context(database_path)
    errors: list[str] = []
    if brief.snapshot_id != context["snapshot_id"]:
        errors.append("snapshot_id does not match the mapped repository")

    file_refs = {f"file:{item['path']}" for item in context["files"]}
    module_refs = {f"module:{item['name']}" for item in context["modules"]}
    import_refs = {
        f"import:{item['source']}->{item['target']}"
        for item in context["imports"]
        if item["target"] is not None
    }
    symbol_refs = {item["id"] for item in context["symbols"]}
    entity_refs = file_refs | module_refs | symbol_refs
    evidence_refs = entity_refs | import_refs

    claimed_evidence = list(brief.purpose.evidence)
    for item in [*brief.technologies, *brief.components, *brief.entry_points, *brief.flows]:
        claimed_evidence.extend(item.evidence)
    for reference in sorted(set(claimed_evidence) - evidence_refs):
        errors.append(f"unknown evidence reference: {reference}")

    for component in brief.components:
        for member in component.members:
            if member not in entity_refs:
                errors.append(f"unknown component member: {member}")
    for item in brief.reading_order:
        if item.target not in entity_refs:
            errors.append(f"unknown reading target: {item.target}")
    for entry_point in brief.entry_points:
        if entry_point.target not in entity_refs:
            errors.append(f"unknown entry-point target: {entry_point.target}")
        if entry_point.status == "confirmed":
            errors.append(
                f"confirmed entry point lacks deterministic support: {entry_point.target}"
            )
    if brief.flows:
        errors.append("flows are unsupported until deterministic call evidence exists")

    if expectation_data is not None:
        try:
            expectations = BriefExpectations.model_validate(expectation_data)
        except ValidationError as error:
            errors.extend(
                f"expectations:{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
                for item in error.errors()
            )
        else:
            errors.extend(_evaluate_expectations(brief, expectations))
    return errors


def _evaluate_expectations(
    brief: RepositoryBrief, expectations: BriefExpectations
) -> list[str]:
    errors: list[str] = []
    purpose = brief.purpose.summary.casefold()
    for term in expectations.purpose_terms:
        if term.casefold() not in purpose:
            errors.append(f"purpose is missing expected term: {term}")

    technologies = {item.name.casefold() for item in brief.technologies}
    for name in expectations.technology_names:
        if name.casefold() not in technologies:
            errors.append(f"missing expected technology: {name}")

    component_members = [set(item.members) for item in brief.components]
    for group in expectations.required_component_member_groups:
        if not any(set(group) <= members for members in component_members):
            errors.append(f"missing component member group: {', '.join(group)}")

    confirmed_count = sum(item.status == "confirmed" for item in brief.entry_points)
    if (
        expectations.maximum_confirmed_entry_points is not None
        and confirmed_count > expectations.maximum_confirmed_entry_points
    ):
        errors.append("too many confirmed entry points")
    if expectations.maximum_flows is not None and len(brief.flows) > expectations.maximum_flows:
        errors.append("too many flows")

    unknowns = "\n".join(brief.unknowns).casefold()
    for term in expectations.required_unknown_terms:
        if term.casefold() not in unknowns:
            errors.append(f"unknowns are missing expected term: {term}")
    return errors
