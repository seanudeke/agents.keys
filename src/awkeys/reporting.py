"""Aggregate output excludes repository identities and raw workflow text."""
from __future__ import annotations

import csv
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

from .io import write_json


def count_percent(count: int, total: int) -> dict:
    return {"count": count, "denominator": total, "percent": 100 * count / total if total else None}


def wilson(successes: int, total: int) -> list[float] | None:
    """Binomial interval, for repeated controlled trials rather than index coverage."""
    if total < 0 or successes < 0 or successes > total:
        raise ValueError("invalid binomial counts")
    if not total:
        return None
    z = 1.959963984540054
    p, n = successes / total, total
    center = (p + z*z/(2*n)) / (1 + z*z/n)
    radius = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return [max(0.0, center - radius), min(1.0, center + radius)]


def _subset(rows: list[dict]) -> dict:
    n = len(rows)
    repositories = {r["repository_id"] for r in rows}
    candidates = {r["repository_id"] for r in rows if r["triple_indicator_candidate"]}
    actions = [a for r in rows for a in r["action_references"] if a["kind"] == "remote"]
    return {
        "agent_jobs": n, "repositories_with_agent_jobs": len(repositories),
        "triple_indicator_jobs": count_percent(sum(r["triple_indicator_candidate"] for r in rows), n),
        "repositories_with_triple_indicator": count_percent(len(candidates), len(repositories)),
        "referenced_model_secret_jobs": count_percent(sum(r["model_secret_reference"] for r in rows), n),
        "referenced_non_model_secret_jobs": count_percent(sum(r["non_model_secret_reference"] for r in rows), n),
        "inherited_or_unknown_token_jobs": count_percent(sum(r["permissions"]["mode"] in ("unknown", "dynamic_or_invalid") for r in rows), n),
        "self_hosted_label_jobs": count_percent(sum(r["runner"] == "self_hosted_lifecycle_unknown" for r in rows), n),
        "unpinned_direct_remote_action_uses": count_percent(sum(a["pinned"] is False for a in actions), len(actions)),
        "a_input_indicator": dict(Counter(r["a_input_indicator"] for r in rows)),
        "b_sensitive_indicator": dict(Counter(r["b_sensitive_indicator"] for r in rows)),
        "c_declared_repository_write": dict(Counter(r["c_declared_repository_write"] for r in rows)),
        "secret_categories_jobs": dict(sorted(Counter(c for r in rows for c in set(r["secret_categories"])).items())),
        "agents_jobs": dict(sorted(Counter(a for r in rows for a in set(r["agents"])).items())),
    }


def summarize(rows: list[dict], manifest: dict | None = None) -> dict:
    identities = set()
    for r in rows:
        if r.get("record_kind") != "configuration_observation":
            raise ValueError("only configuration observations can enter a census summary")
        key = (r["repository_id"], r["workflow_path"], r["job_id"])
        if key in identities:
            raise ValueError("duplicate repository/workflow/job; aggregate one snapshot at a time")
        identities.add(key)
    game = [r for r in rows if r["engines"]]
    non_game = [r for r in rows if not r["engines"] and r["engine_detection_complete"]]
    unknown = [r for r in rows if not r["engines"] and not r["engine_detection_complete"]]
    result = {
        "schema_version": 1, "report_kind": "descriptive_configuration_summary",
        "interpretation": "Nonprobability index or explicit-list sample. Indicators are not confirmed vulnerabilities.",
        "population_prevalence_confidence_interval": None,
        "all": _subset(rows), "game_markers_present": _subset(game),
        "no_engine_marker_complete_tree": _subset(non_game),
        "engine_classification_unknown": _subset(unknown),
        "per_engine": {engine: _subset([r for r in rows if engine in r["engines"]])
                       for engine in ("unity", "unreal", "godot")},
    }
    if manifest:
        result["collection"] = {k: manifest.get(k) for k in (
            "started_at", "finished_at", "request_count", "collection_mode",
            "discovered_repository_count", "repository_budget_truncated",
            "search_returned_pages_complete", "snapshot_analysis_complete", "index_population_exhaustive")}
        result["collection"]["repository_status_counts"] = dict(Counter(x["status"] for x in manifest.get("repositories", [])))
        result["collection"]["error_count"] = len(manifest.get("errors", []))
    return result


def validation_sample(rows: list[dict], count: int, seed: int = 20261018) -> list[dict]:
    if count < 0:
        raise ValueError("sample count must be nonnegative")
    unique = {}
    for r in rows:
        key = (r["repository_id"], r["workflow_path"], r["job_id"])
        unique[key] = r
    ordered = [unique[k] for k in sorted(unique)]
    selected = random.Random(seed).sample(ordered, min(count, len(ordered)))
    # Blind to scanner classifications. Resolve source through the private manifest.
    return [{"repository_id": r["repository_id"], "workflow_path": r["workflow_path"], "job_id": r["job_id"],
             "workflow_sha256": r["workflow_sha256"], "reviewer": "", "a_input_indicator": "",
             "b_sensitive_indicator": "", "c_declared_repository_write": "", "notes": ""}
            for r in selected]


def write_review_csv(path: Path, rows: list[dict]) -> None:
    fields = ["repository_id", "workflow_path", "job_id", "workflow_sha256", "reviewer",
              "a_input_indicator", "b_sensitive_indicator", "c_declared_repository_write", "notes"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fields)
        writer.writeheader()
        writer.writerows(rows)


def reviewer_agreement(left: list[dict], right: list[dict]) -> dict:
    def index(rows):
        result = {}
        for r in rows:
            key = (r["repository_id"], r["workflow_path"], r["workflow_sha256"], r["job_id"])
            if key in result:
                raise ValueError("duplicate review item")
            result[key] = r
        return result
    a, b = index(left), index(right)
    if set(a) != set(b):
        raise ValueError("reviewers must label the identical sample")
    out = {}
    for field in ("a_input_indicator", "b_sensitive_indicator", "c_declared_repository_write"):
        pairs = [(a[k][field], b[k][field]) for k in sorted(a)]
        if any(x not in ("present", "absent", "unknown") for p in pairs for x in p):
            raise ValueError("all labels must be present, absent or unknown")
        n = len(pairs)
        observed = sum(x == y for x, y in pairs) / n if n else None
        ca, cb = Counter(x for x, _ in pairs), Counter(y for _, y in pairs)
        expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n*n) if n else None
        kappa = (observed - expected) / (1 - expected) if n and expected < 1 else None
        out[field] = {"paired_items": n, "observed_agreement": observed, "cohens_kappa": kappa,
                      "marginal_left": dict(ca), "marginal_right": dict(cb)}
    return out
