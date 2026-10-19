from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from . import __version__
from .broker import Context, Rejected, boundary_checks, validate_proposal
from .evaluation import TrialError, summarize_trials
from .github import GitHubClient, GitHubError
from .cache import RecordedGitHubClient
from .io import read_jsonl, write_json, write_jsonl
from .mining import collect
from .reporting import reviewer_agreement, summarize, validation_sample, write_review_csv
from .scanner import WorkflowError, engine_markers, load_catalog, scan_workflow


def local_scan(root: Path, output: Path, repository_id: str, catalog: dict) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("scan requires a repository directory")
    paths, complete = [], True
    for directory, directories, filenames in os.walk(root, followlinks=False):
        directories[:] = sorted(x for x in directories if x not in (".git", ".venv", "node_modules")
                                and not (Path(directory) / x).is_symlink())
        for filename in sorted(filenames):
            path = Path(directory) / filename
            if not path.is_symlink():
                paths.append(path.relative_to(root).as_posix())
            if len(paths) >= 200_000:
                complete = False
                break
        if not complete:
            break
    engines = engine_markers(paths)
    directory = root / ".github" / "workflows"
    rows, errors = [], []
    for path in sorted(directory.glob("*")):
        if path.suffix not in (".yml", ".yaml") or not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            errors.append({"path": path.name, "reason": "symlink_not_followed"})
            continue
        try:
            if path.stat().st_size > 1_048_576:
                raise WorkflowError("workflow exceeds byte limit")
            rows.extend(scan_workflow(path.read_text(encoding="utf-8"), repository_id=repository_id,
                                      path=path.relative_to(root).as_posix(), catalog=catalog,
                                      engines=engines, engine_tree_complete=complete))
        except (WorkflowError, UnicodeError) as exc:
            errors.append({"path": path.name, "reason": type(exc).__name__})
    write_jsonl(output, rows)
    report = {"record_kind": "local_scan_status", "observations": len(rows), "errors": errors,
              "engine_scan_complete_with_documented_exclusions": complete,
              "excluded_directories": [".git", ".venv", "node_modules"]}
    write_json(output.with_suffix(".status.json"), report)
    return report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Agents With Keys: read-only workflow measurement and evidence checks")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="analyze local workflow configuration; execute no project code")
    scan.add_argument("repository", type=Path)
    scan.add_argument("--output", type=Path, required=True)
    scan.add_argument("--repository-id", default="local-study-repository")
    scan.add_argument("--catalog", type=Path)
    mine = sub.add_parser("mine", aliases=["collect"], help="collect public default-branch snapshots through authenticated read-only requests")
    mine.add_argument("--output", type=Path, required=True)
    mine.add_argument("--repositories", type=Path, help="optional newline-separated owner/repo list")
    mine.add_argument("--catalog", type=Path)
    mine.add_argument("--max-repositories", type=int, default=100)
    mine.add_argument("--max-requests", type=int, default=300)
    mine.add_argument("--search-pages-per-query", type=int, help="bounded best-match pages (1-10); omitted uses size partitioning")
    mine.add_argument("--response-cache", type=Path, help="replay privately retained, integrity-checked API responses without network access")
    report = sub.add_parser("summarize", help="export aggregate configuration counts without repository identifiers")
    report.add_argument("observations", type=Path)
    report.add_argument("--manifest", type=Path)
    report.add_argument("--output", type=Path, required=True)
    sample = sub.add_parser("validation-sample", help="draw a reproducible sample with blank independent-review fields")
    sample.add_argument("observations", type=Path)
    sample.add_argument("--count", type=int, default=100)
    sample.add_argument("--seed", type=int, default=20261018)
    sample.add_argument("--output", type=Path, required=True)
    agreement = sub.add_parser("agreement", help="check independent CSV labels and calculate agreement")
    agreement.add_argument("reviewer_a", type=Path)
    agreement.add_argument("reviewer_b", type=Path)
    agreement.add_argument("--output", type=Path, required=True)
    boundary = sub.add_parser("boundary-checks", help="run in-memory validator checks, never empirical agent trials")
    boundary.add_argument("--output", type=Path, required=True)
    proposal = sub.add_parser("validate-proposal", help="validate a closed-schema proposal; do not execute any writes")
    proposal.add_argument("proposal", type=Path)
    proposal.add_argument("--repository", required=True)
    proposal.add_argument("--issue", type=int, required=True)
    proposal.add_argument("--run-id", required=True)
    proposal.add_argument("--source-sha", required=True)
    proposal.add_argument("--output", type=Path, required=True)
    evaluate = sub.add_parser("evaluate", help="verify evidence files and summarize recorded real-agent trials")
    evaluate.add_argument("trials", type=Path)
    evaluate.add_argument("--evidence-root", type=Path, required=True)
    evaluate.add_argument("--output", type=Path, required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "scan":
            status = local_scan(args.repository, args.output, args.repository_id, load_catalog(args.catalog))
            print(json.dumps(status, sort_keys=True))
            return 2 if status["errors"] else 0
        if args.command in ("mine", "collect"):
            token = os.environ.get("AWKEYS_GITHUB_TOKEN") or os.environ.get("GITHUB_TOKEN", "")
            client = (RecordedGitHubClient(args.response_cache, max_requests=args.max_requests)
                      if args.response_cache else GitHubClient(token, max_requests=args.max_requests))
            names = None
            if args.repositories:
                names = [line.strip() for line in args.repositories.read_text().splitlines()
                         if line.strip() and not line.lstrip().startswith("#")]
            manifest = collect(client, output=args.output, catalog=load_catalog(args.catalog),
                               repositories=names, max_repositories=args.max_repositories,
                               search_pages_per_query=args.search_pages_per_query)
            print(json.dumps({"observations": manifest["observation_count"],
                              "snapshot_analysis_complete": manifest["snapshot_analysis_complete"],
                              "index_population_exhaustive": False}))
            return 0 if manifest["snapshot_analysis_complete"] else 2
        if args.command == "summarize":
            manifest = json.loads(args.manifest.read_text()) if args.manifest else None
            write_json(args.output, summarize(read_jsonl(args.observations), manifest))
        elif args.command == "validation-sample":
            write_review_csv(args.output, validation_sample(read_jsonl(args.observations), args.count, args.seed))
        elif args.command == "agreement":
            with args.reviewer_a.open(newline="", encoding="utf-8") as a, args.reviewer_b.open(newline="", encoding="utf-8") as b:
                write_json(args.output, reviewer_agreement(list(csv.DictReader(a)), list(csv.DictReader(b))))
        elif args.command == "boundary-checks":
            result = boundary_checks()
            write_json(args.output, result)
            return 0 if all(x["check_passed"] for x in result["checks"]) else 1
        elif args.command == "validate-proposal":
            context = Context(args.repository, args.issue, args.run_id, args.source_sha)
            write_json(args.output, validate_proposal(args.proposal.read_bytes(), context))
        elif args.command == "evaluate":
            write_json(args.output, summarize_trials(read_jsonl(args.trials), args.evidence_root))
        return 0
    except (ValueError, OSError, GitHubError) as exc:
        # Keep GitHub errors sanitized; parser errors intentionally omit source lines.
        print(f"awkeys: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
