#!/usr/bin/env python3
"""Snapshot ONE public repo by blobless clone and append scanner records.

Usage: scan_one.py <owner/repo> <obs.jsonl> <status.jsonl>
Keeps the project's scanner unchanged; only the fetch layer is clone-based.
No repository code is executed; only workflow YAML text is read.
"""
from __future__ import annotations
import hashlib, hmac, json, os, re, signal, subprocess, sys, tempfile
from pathlib import Path

import os as _os, sys as _sys; _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "src"))
from awkeys.scanner import MAX_BYTES, WorkflowError, engine_markers, load_catalog, scan_workflow  # noqa: E402
from awkeys.io import now, sha256  # noqa: E402

WF_RE = re.compile(r"\.github/workflows/[^/]+\.ya?ml$")
SALT = b"agents-with-keys-public-sample-salt"  # fixed so repo ids are stable across runs


def rid(name): return hmac.new(SALT, name.lower().encode(), hashlib.sha256).hexdigest()[:16]


def clone(name, dest):
    env = dict(os.environ, GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
    p = subprocess.Popen(["git", "clone", "--depth", "1", "--filter=blob:none", "--no-checkout",
                          f"https://github.com/{name}", dest],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
    try:
        return p.wait(timeout=45) == 0
    except subprocess.TimeoutExpired:
        try: os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError: pass
        p.wait(); return False


def git(args, cwd, timeout=30):
    return subprocess.run(["git", "-C", cwd] + args, capture_output=True, text=True, timeout=timeout)


def main(name, obs_path, status_path):
    catalog = load_catalog()
    status = {"repository_id": rid(name), "full_name": name, "status": "pending", "at": now()}
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        dest = os.path.join(tmp, "r")
        if not clone(name, dest):
            status["status"] = "clone_timeout_or_failed"
        else:
            try:
                head = git(["rev-parse", "HEAD"], dest).stdout.strip()
                tree = git(["ls-tree", "-r", "--name-only", "HEAD"], dest, timeout=40)
                paths = [ln for ln in tree.stdout.splitlines() if ln]
                engines = engine_markers(paths)
                wf = sorted(p for p in paths if WF_RE.search(p))
                status.update(commit=head, engines=engines, workflow_count=0, agent_job_count=0)
                for p in wf:
                    blob = git(["cat-file", "-p", f"HEAD:{p}"], dest)
                    if blob.returncode != 0 or len(blob.stdout.encode("utf-8")) > MAX_BYTES:
                        continue
                    status["workflow_count"] += 1
                    try:
                        rows = scan_workflow(blob.stdout, repository_id=rid(name), path=p, commit=head,
                                             catalog=catalog, engines=engines, engine_tree_complete=True)
                        records.extend(rows); status["agent_job_count"] += len(rows)
                    except (WorkflowError, UnicodeError):
                        pass
                status["status"] = "analyzed"
            except subprocess.TimeoutExpired:
                status["status"] = "tree_timeout"
            except Exception as exc:  # noqa: BLE001
                status["status"] = "error"; status["reason"] = type(exc).__name__
    with open(obs_path, "a", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    with open(status_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(status) + "\n")
    print(f"{name}: {status['status']} wf={status.get('workflow_count','-')} jobs={status.get('agent_job_count','-')} engines={status.get('engines','-')}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
