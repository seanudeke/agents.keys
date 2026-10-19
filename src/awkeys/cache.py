"""Offline replay of retained read-only API responses, never a live HTTP client.

Each response must carry its capture time, transport provenance, and SHA-256.
The digest checks retained bytes; it does not authenticate the remote server.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .github import BudgetExceeded, GitHubError
from .io import now


def request_key(path: str, params: dict | None = None) -> str:
    if not path.startswith("/") or path.startswith("//") or "://" in path:
        raise GitHubError("only GitHub API paths are accepted")
    return hashlib.sha256(json.dumps([path, params or {}], sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def response_digest(response) -> str:
    return hashlib.sha256(json.dumps(response, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class RecordedGitHubClient:
    def __init__(self, directory: Path, *, max_requests: int = 300):
        if max_requests < 1:
            raise ValueError("max_requests must be positive")
        self.directory, self.max_requests = Path(directory), max_requests
        self.requests, self.audit = 0, []

    def get(self, path: str, params: dict | None = None):
        if self.requests >= self.max_requests:
            raise BudgetExceeded("recorded-response request budget exhausted")
        key = request_key(path, params)
        self.requests += 1
        try:
            entry = json.loads((self.directory / (key + ".json")).read_text())
            response = entry["response"]
            if (entry["path"] != path or entry["params"] != (params or {}) or
                    not entry["captured_at"] or not entry["transport"] or
                    entry["response_sha256"] != response_digest(response) or
                    not isinstance(response, (dict, list))):
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError):
            self.audit.append({"path": path, "params": params or {}, "status": "cache_missing_or_invalid"})
            raise GitHubError("recorded API response missing or invalid") from None
        self.audit.append({"path": path, "params": params or {}, "at": entry["captured_at"],
                           "status": 200, "transport": entry["transport"],
                           "response_sha256": entry["response_sha256"], "replayed_at": now()})
        return response
