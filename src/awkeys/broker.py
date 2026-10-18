"""Example deterministic output validator, not an agent sandbox or authorization proof."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


class Rejected(ValueError):
    pass


@dataclass(frozen=True)
class Context:
    repository: str
    issue: int
    run_id: str
    source_sha: str
    allowed_labels: tuple[str, ...] = ("needs-triage", "documentation")


def validate_proposal(raw: bytes, context: Context) -> dict:
    if len(raw) > 4096:
        raise Rejected("proposal exceeds byte limit")
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Rejected("duplicate JSON key")
            result[key] = value
        return result
    try:
        proposal = json.loads(raw, object_pairs_hook=object_pairs)
    except (ValueError, UnicodeError, RecursionError):
        raise Rejected("invalid JSON proposal") from None
    expected = {"version", "operation", "repository", "issue", "run_id", "source_sha", "labels"}
    if not isinstance(proposal, dict) or set(proposal) != expected:
        raise Rejected("proposal fields do not match the closed schema")
    if type(proposal["version"]) is not int or proposal["version"] != 1:
        raise Rejected("unsupported schema version")
    if proposal["operation"] != "add_labels":
        raise Rejected("operation is not authorized")
    if (proposal["repository"], proposal["run_id"], proposal["source_sha"]) != (
            context.repository, context.run_id, context.source_sha):
        raise Rejected("proposal does not match the trusted run context")
    if type(proposal["issue"]) is not int or proposal["issue"] != context.issue or context.issue < 1:
        raise Rejected("issue is not authorized")
    if not re.fullmatch(r"[0-9a-f]{40}", context.source_sha):
        raise Rejected("trusted context requires an immutable source SHA")
    labels = proposal["labels"]
    if not isinstance(labels, list) or not 1 <= len(labels) <= 2:
        raise Rejected("label count is outside policy")
    if any(not isinstance(x, str) or x not in context.allowed_labels for x in labels):
        raise Rejected("label is outside policy")
    if len(set(labels)) != len(labels):
        raise Rejected("duplicate label")
    return {"version": 1, "operation": "add_labels", "repository": context.repository,
            "issue": context.issue, "run_id": context.run_id, "source_sha": context.source_sha,
            "labels": sorted(labels),
            "proposal_sha256": hashlib.sha256(raw).hexdigest(),
            "execution_authorized_by_validator": False}


def boundary_checks() -> dict:
    """Harmless in-memory fixtures; deliberately not empirical LLM attack trials."""
    context = Context("research-owner/sandbox", 1, "fixture-run", "a"*40)
    base = {"version": 1, "operation": "add_labels", "repository": context.repository,
            "issue": 1, "run_id": context.run_id, "source_sha": context.source_sha,
            "labels": ["needs-triage"]}
    cases = [
        ("authorized_label", {}, True),
        ("repository_confusion", {"repository": "another-owner/another-repository"}, False),
        ("issue_confusion", {"issue": 2}, False),
        ("run_confusion", {"run_id": "other-run"}, False),
        ("source_confusion", {"source_sha": "b"*40}, False),
        ("unauthorized_operation", {"operation": "publish_release"}, False),
        ("shell_field", {"command": "FIXTURE_ONLY_NO_COMMAND_IS_EXECUTED"}, False),
        ("arbitrary_content", {"labels": ["https://example.invalid/fixture"]}, False),
        ("oversized_label_list", {"labels": ["needs-triage"]*3}, False),
        ("boolean_issue", {"issue": True}, False),
    ]
    results = []
    for case, changes, expected in cases:
        proposal = {**base, **changes}
        try:
            validate_proposal(json.dumps(proposal).encode(), context)
            accepted = True
        except Rejected:
            accepted = False
        results.append({"case_id": case, "expected_acceptance": expected,
                        "observed_acceptance": accepted, "check_passed": accepted == expected})
    return {"schema_version": 1, "record_kind": "deterministic_boundary_fixture_check",
            "empirical_agent_evaluation": False,
            "interpretation": "Checks this validator's closed schema only; does not measure prompt-injection resistance or task utility.",
            "checks": results}
