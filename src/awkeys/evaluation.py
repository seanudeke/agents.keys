"""Validate and summarize evidence-backed controlled agent trials.

An external agent runner must write observations and evidence files. This module
does not fabricate outcomes or silently treat fixture tests as model experiments.
"""
from __future__ import annotations

import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

from .io import read_jsonl, sha256
from .reporting import count_percent, wilson


class TrialError(ValueError):
    pass


HASH = re.compile(r"^[0-9a-f]{64}$")
KEY = ("provider", "model", "task_id", "attack_id", "repetition")
FIELDS = {
    "record_kind", "trial_id", "protocol_sha256", "corpus_sha256", "configuration_sha256",
    "provider", "model", "agent_version", "action_sha", "task_id", "attack_id", "repetition",
    "variant", "started_at", "status", "attacker_success", "task_success",
    "elapsed_seconds", "input_tokens", "output_tokens", "evidence",
}


def validate_trials(rows: list[dict], evidence_root: Path) -> list[dict]:
    seen, trial_ids = set(), set()
    root = evidence_root.resolve()
    for row in rows:
        if set(row) != FIELDS:
            raise TrialError("trial fields do not match the version 1 schema")
        if row["record_kind"] != "agent_trial":
            raise TrialError("fixtures and boundary checks cannot enter empirical results")
        for field in ("trial_id", "provider", "model", "agent_version", "task_id", "attack_id", "started_at"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise TrialError(f"nonempty {field} is required")
        from datetime import datetime
        try:
            stamp = datetime.fromisoformat(row["started_at"].replace("Z", "+00:00"))
            if stamp.utcoffset() is None:
                raise ValueError()
        except ValueError:
            raise TrialError("started_at must include a timezone") from None
        if not isinstance(row["action_sha"], str) or not re.fullmatch(r"[0-9a-f]{40}", row["action_sha"]):
            raise TrialError("action_sha must identify an immutable action revision")
        for field in ("protocol_sha256", "corpus_sha256", "configuration_sha256"):
            if not isinstance(row[field], str) or not HASH.fullmatch(row[field]):
                raise TrialError(f"{field} is required")
        if row["variant"] not in ("baseline", "profile"):
            raise TrialError("unknown configuration variant")
        if type(row["repetition"]) is not int or row["repetition"] < 0:
            raise TrialError("repetition must be a nonnegative integer")
        key = tuple(row[x] for x in KEY) + (row["variant"],)
        if key in seen or row["trial_id"] in trial_ids:
            raise TrialError("duplicate trial or paired condition")
        seen.add(key)
        trial_ids.add(row["trial_id"])
        if row["status"] not in ("completed", "error"):
            raise TrialError("invalid trial status")
        completed = row["status"] == "completed"
        for field in ("attacker_success", "task_success"):
            if completed and type(row[field]) is not bool:
                raise TrialError("completed trials need independently assessed Boolean outcomes")
            if not completed and row[field] is not None:
                raise TrialError("errors require null outcomes; they are not successful defenses")
        elapsed = row["elapsed_seconds"]
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise TrialError("elapsed_seconds must be finite and nonnegative")
        for field in ("input_tokens", "output_tokens"):
            value = row[field]
            if value is not None and (type(value) is not int or value < 0):
                raise TrialError("token counts must be nonnegative integers or null")
        evidence = row["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise TrialError("each trial needs evidence files")
        roles = set()
        for item in evidence:
            if not isinstance(item, dict) or set(item) != {"path", "sha256", "role"}:
                raise TrialError("invalid evidence object")
            if not isinstance(item["role"], str) or item["role"] not in {
                    "execution_log", "outcome_oracle", "protocol", "corpus", "configuration"}:
                raise TrialError("unknown evidence role")
            if not isinstance(item["path"], str) or Path(item["path"]).is_absolute():
                raise TrialError("evidence paths must be relative")
            if not isinstance(item["sha256"], str) or not HASH.fullmatch(item["sha256"]):
                raise TrialError("evidence requires a SHA-256")
            target = (root / item["path"]).resolve()
            if not target.is_relative_to(root) or not target.is_file():
                raise TrialError("evidence is missing or outside the evidence directory")
            if target.stat().st_size > 67_108_864:
                raise TrialError("evidence file exceeds 64 MiB")
            if sha256(target.read_bytes()) != item["sha256"]:
                raise TrialError("evidence hash mismatch")
            roles.add(item["role"])
            expected_hash_field = {"protocol": "protocol_sha256", "corpus": "corpus_sha256",
                                   "configuration": "configuration_sha256"}.get(item["role"])
            if expected_hash_field and row[expected_hash_field] != item["sha256"]:
                raise TrialError("declared protocol, corpus or configuration does not match its evidence")
            if completed and item["role"] == "outcome_oracle":
                import json
                try:
                    oracle = json.loads(target.read_text(encoding="utf-8"))
                    if any(type(oracle[field]) is not bool or oracle[field] != row[field]
                           for field in ("attacker_success", "task_success")):
                        raise ValueError()
                except (ValueError, KeyError, TypeError, UnicodeError):
                    raise TrialError("outcome oracle does not match the recorded outcomes") from None
        required_roles = {"execution_log", "protocol", "corpus", "configuration"}
        if completed:
            required_roles.add("outcome_oracle")
        if not required_roles <= roles:
            raise TrialError("required execution log and outcome oracle are missing")
    protocols = {r["protocol_sha256"] for r in rows}
    corpora = {r["corpus_sha256"] for r in rows}
    if len(protocols) > 1 or len(corpora) > 1:
        raise TrialError("summarize one frozen protocol and corpus at a time")
    versions = defaultdict(set)
    configurations = defaultdict(set)
    for row in rows:
        versions[(row["provider"], row["model"])].add((row["agent_version"], row["action_sha"]))
        configurations[(row["provider"], row["model"], row["variant"])].add(row["configuration_sha256"])
    if any(len(x) > 1 for x in versions.values()) or any(len(x) > 1 for x in configurations.values()):
        raise TrialError("split changed implementation revisions or configurations into separate analyses")
    return rows


def summarize_trials(rows: list[dict], evidence_root: Path) -> dict:
    validate_trials(rows, evidence_root)
    grouped = defaultdict(list)
    pairs = defaultdict(dict)
    for row in rows:
        grouped[(row["provider"], row["model"], row["attack_id"], row["variant"])].append(row)
        pairs[tuple(row[x] for x in KEY)][row["variant"]] = row
    groups = []
    for key, observations in sorted(grouped.items()):
        completed = [x for x in observations if x["status"] == "completed"]
        n = len(completed)
        attacks = sum(x["attacker_success"] for x in completed)
        utility = sum(x["task_success"] for x in completed)
        times = [x["elapsed_seconds"] for x in completed]
        tokens = [x["input_tokens"] + x["output_tokens"] for x in completed
                  if x["input_tokens"] is not None and x["output_tokens"] is not None]
        attack_n = n if key[2] != "clean" else 0
        groups.append({
            **dict(zip(("provider", "model", "attack_id", "variant"), key)),
            "attempted": len(observations), "completed": n,
            "errors": len(observations) - n,
            "condition_type": "clean" if key[2] == "clean" else "attacked",
            "attacker_success": count_percent(attacks, attack_n) if attack_n else count_percent(0, 0),
            "attack_not_successful": count_percent(n-attacks, attack_n) if attack_n else count_percent(0, 0),
            "task_success": count_percent(utility, n),
            "attacker_success_wilson95": wilson(attacks, attack_n) if attack_n else None,
            "interval_interpretation": "Conditional binomial interval; repeated tasks and adaptive trials may be dependent.",
            "median_elapsed_seconds": statistics.median(times) if times else None,
            "median_total_tokens": statistics.median(tokens) if tokens else None,
            "token_observation_count": len(tokens),
        })
    complete_pairs = [p for p in pairs.values() if set(p) == {"baseline", "profile"}
                      and all(x["status"] == "completed" for x in p.values())]
    # Pair comparability: exact implementation versions and data are required.
    for pair in complete_pairs:
        a, b = pair["baseline"], pair["profile"]
        if a["agent_version"] != b["agent_version"] or a["action_sha"] != b["action_sha"]:
            raise TrialError("a paired comparison changed agent/action revision")
    baseline_succeeded = [p for p in complete_pairs if p["baseline"]["attacker_success"]]
    prevented = sum(not p["profile"]["attacker_success"] for p in baseline_succeeded)
    unchallenged = [p for p in complete_pairs if p["baseline"]["task_success"]]
    retained = sum(p["profile"]["task_success"] for p in unchallenged)
    clean = [p for p in unchallenged if p["baseline"]["attack_id"] == "clean"]
    attacked = [p for p in unchallenged if p["baseline"]["attack_id"] != "clean"]
    elapsed_differences = [p["profile"]["elapsed_seconds"]-p["baseline"]["elapsed_seconds"] for p in complete_pairs]
    elapsed_ratios = [p["profile"]["elapsed_seconds"]/p["baseline"]["elapsed_seconds"]
                      for p in complete_pairs if p["baseline"]["elapsed_seconds"] > 0]
    token_ratios = []
    for p in complete_pairs:
        a, b = p["baseline"], p["profile"]
        values = [x[field] for x in (a, b) for field in ("input_tokens", "output_tokens")]
        if all(x is not None for x in values) and a["input_tokens"] + a["output_tokens"] > 0:
            token_ratios.append((b["input_tokens"]+b["output_tokens"])/(a["input_tokens"]+a["output_tokens"]))
    return {
        "schema_version": 1, "report_kind": "evidence_backed_recorded_agent_trials",
        "groups": groups, "complete_pairs": len(complete_pairs),
        "unpaired_or_failed_pairs": len(pairs)-len(complete_pairs),
        "prevented_among_baseline_successful_attacks": count_percent(prevented, len(baseline_succeeded)),
        "utility_retained_among_baseline_successful_tasks": count_percent(retained, len(unchallenged)),
        "clean_utility_retained": count_percent(sum(p["profile"]["task_success"] for p in clean), len(clean)),
        "attacked_utility_retained": count_percent(sum(p["profile"]["task_success"] for p in attacked), len(attacked)),
        "paired_overhead": {
            "median_elapsed_difference_seconds": statistics.median(elapsed_differences) if elapsed_differences else None,
            "median_elapsed_ratio_profile_to_baseline": statistics.median(elapsed_ratios) if elapsed_ratios else None,
            "elapsed_ratio_pair_count": len(elapsed_ratios),
            "median_token_ratio_profile_to_baseline": statistics.median(token_ratios) if token_ratios else None,
            "token_ratio_pair_count": len(token_ratios),
        },
        "interpretation": "Recorded observations, not an independent replication or proof. Evidence hashes check integrity, not truth or oracle validity.",
    }
