"""Default-branch snapshots of public repositories. No repository code is run."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from . import __version__
from .github import GitHubError, search_partitioned
from .io import now, sha256, write_json, write_jsonl
from .scanner import MAX_BYTES, WorkflowError, engine_markers, scan_workflow

REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def repository_id(name: str, salt: bytes) -> str:
    return hmac.new(salt, name.lower().encode(), hashlib.sha256).hexdigest()


def search_queries(catalog: dict) -> list[str]:
    # Search membership is an index sample, not a random sample or a global census.
    return sorted({f'"{x["uses"]}" path:.github/workflows is:public' for x in catalog["actions"]})


def _decode_blob(blob: dict) -> bytes:
    if blob.get("encoding") != "base64" or not isinstance(blob.get("content"), str):
        raise GitHubError("unsupported blob encoding")
    try:
        data = base64.b64decode(blob["content"], validate=False)
    except (ValueError, TypeError):
        raise GitHubError("invalid blob encoding") from None
    if len(data) > MAX_BYTES:
        raise GitHubError("workflow exceeds scanner byte limit")
    return data


def collect(client, *, output: Path, catalog: dict, repositories: list[str] | None = None,
            max_repositories: int = 100) -> dict:
    if max_repositories < 1:
        raise ValueError("max_repositories must be positive")
    if output.exists() and any(output.iterdir()):
        raise ValueError("choose a new empty output directory to preserve prior runs")
    output.mkdir(parents=True, exist_ok=True)
    output.chmod(0o700)
    salt = os.urandom(32)
    salt_path = output / "identity-salt.bin"
    salt_path.write_bytes(salt)
    salt_path.chmod(0o600)
    started = now()
    manifest = {
        "schema_version": 1, "tool_version": __version__, "started_at": started,
        "finished_at": None, "collection_mode": "explicit_repository_list" if repositories else "action_catalog_search",
        "catalog_sha256": sha256(json.dumps(catalog, sort_keys=True).encode()),
        "max_repositories": max_repositories,
        "search_leaves": [], "repositories": [], "errors": [],
        "search_returned_pages_complete": False, "index_population_exhaustive": False,
        "snapshot_analysis_complete": False,
        "statistical_design": "nonprobability_observational_configuration_sample",
    }
    records, names = [], list(dict.fromkeys(repositories or []))
    search_done = repositories is not None
    truncated_by_repo_budget = False
    try:
        if repositories is None:
            for query in search_queries(catalog):
                hits, leaves = search_partitioned(client, query)
                manifest["search_leaves"].extend(leaves)
                names.extend(x["repository"]["full_name"] for x in hits)
            names = sorted(set(names))
            search_done = True
        truncated_by_repo_budget = len(names) > max_repositories
        manifest["discovered_repository_count"] = len(names)
        for name in names[:max_repositories]:
            if not REPOSITORY.fullmatch(name):
                manifest["errors"].append({"stage": "repository_name", "reason": "invalid owner/name"})
                continue
            rid = repository_id(name, salt)
            item = {"repository_id": rid, "full_name": name, "status": "pending"}
            manifest["repositories"].append(item)
            try:
                meta = client.get("/repos/" + name)
                if meta.get("private") is not False:
                    item.update(status="excluded", reason="not_confirmed_public")
                    continue
                if meta.get("fork") or meta.get("archived"):
                    item.update(status="excluded", reason="fork_or_archived")
                    continue
                branch = meta["default_branch"]
                revision = client.get(f"/repos/{name}/commits/{quote(branch, safe='')}")
                commit = revision["sha"]
                tree_sha = revision["commit"]["tree"]["sha"]
                tree = client.get(f"/repos/{name}/git/trees/{tree_sha}", {"recursive": 1})
                paths = [x["path"] for x in tree.get("tree", []) if x.get("type") == "blob"]
                engines = engine_markers(paths)
                tree_complete = not bool(tree.get("truncated"))
                item.update(commit=commit, default_branch=branch, stars=meta.get("stargazers_count"),
                            topics=meta.get("topics", []), engines=engines,
                            engine_tree_complete=tree_complete, workflow_count=0, agent_job_count=0)
                workflows = [x for x in tree.get("tree", [])
                             if x.get("type") == "blob" and re.fullmatch(r"\.github/workflows/[^/]+\.ya?ml", x.get("path", ""))]
                repo_errors = False
                for entry in sorted(workflows, key=lambda x: x["path"]):
                    if entry.get("size", 0) > MAX_BYTES:
                        manifest["errors"].append({"repository_id": rid, "stage": "workflow_size"})
                        repo_errors = True
                        continue
                    blob = client.get(f"/repos/{name}/git/blobs/{entry['sha']}")
                    raw = _decode_blob(blob)
                    digest = sha256(raw)
                    raw_path = output / "raw" / rid / f"{digest}.yml"
                    raw_path.parent.mkdir(parents=True, exist_ok=True)
                    raw_path.write_bytes(raw)
                    item["workflow_count"] += 1
                    try:
                        rows = scan_workflow(raw.decode("utf-8"), repository_id=rid, path=entry["path"],
                                             commit=commit, catalog=catalog, engines=engines,
                                             engine_tree_complete=tree_complete)
                        records.extend(rows)
                        item["agent_job_count"] += len(rows)
                    except (WorkflowError, UnicodeError):
                        manifest["errors"].append({"repository_id": rid, "workflow_sha256": digest,
                                                   "stage": "workflow_parse"})
                        repo_errors = True
                item["status"] = "partial" if repo_errors or not tree_complete else "analyzed"
            except (GitHubError, KeyError, TypeError, ValueError) as exc:
                item.update(status="error", reason=type(exc).__name__)
                manifest["errors"].append({"repository_id": rid, "stage": "snapshot", "reason": type(exc).__name__})
                # Budget exhaustion must terminate rather than creating thousands of error records.
                if client.requests >= client.max_requests:
                    raise
    except KeyboardInterrupt:
        manifest["errors"].append({"stage": "interrupted", "reason": "KeyboardInterrupt"})
    except (GitHubError, KeyError, TypeError, ValueError) as exc:
        manifest["errors"].append({"stage": "collection", "reason": type(exc).__name__})
    finally:
        manifest["finished_at"] = now()
        manifest["request_count"] = client.requests
        manifest["repository_budget_truncated"] = truncated_by_repo_budget
        manifest["search_returned_pages_complete"] = (
            search_done and not truncated_by_repo_budget
            and all(x["returned_pages_complete"] for x in manifest["search_leaves"])
            and not any(x["stage"] == "collection" for x in manifest["errors"]))
        manifest["snapshot_analysis_complete"] = (
            manifest["search_returned_pages_complete"]
            and all(x["status"] in ("analyzed", "excluded") for x in manifest["repositories"])
            and not manifest["errors"])
        manifest["observation_count"] = len(records)
        write_jsonl(output / "observations.jsonl", records)
        write_json(output / "manifest.private.json", manifest)
        write_json(output / "requests.private.json", client.audit)
        write_json(output / "catalog.json", catalog)
    return manifest
