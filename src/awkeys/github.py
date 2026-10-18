"""Read-only GitHub REST client. Tokens never leave api.github.com."""
from __future__ import annotations

import json
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .io import now


class GitHubError(RuntimeError):
    pass


class BudgetExceeded(GitHubError):
    pass


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward an Authorization header to redirects.
        return None


class GitHubClient:
    def __init__(self, token: str, *, max_requests: int = 300,
                 sleep: Callable = time.sleep, clock: Callable = time.monotonic):
        if not token or any(c.isspace() for c in token):
            raise GitHubError("a nonempty token without whitespace is required")
        if max_requests < 1:
            raise ValueError("max_requests must be positive")
        self._token = token
        self.max_requests = max_requests
        self.requests = 0
        self.sleep, self.clock = sleep, clock
        self.last_search = float("-inf")
        self.audit: list[dict] = []
        self._opener = build_opener(NoRedirect())

    def get(self, path: str, params: dict | None = None) -> dict:
        if not path.startswith("/") or path.startswith("//") or "://" in path:
            raise GitHubError("only GitHub API paths are accepted")
        query = "?" + urlencode(params) if params else ""
        url = "https://api.github.com" + path + query
        is_search = path.startswith("/search/")
        for attempt in range(3):
            if self.requests >= self.max_requests:
                raise BudgetExceeded("request budget exhausted; collection is incomplete")
            if is_search:
                self.sleep(max(0, 6.2 - (self.clock() - self.last_search)))
                self.last_search = self.clock()
            self.requests += 1
            started = now()
            req = Request(url, headers={
                "Authorization": "Bearer " + self._token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "agents-with-keys-research/0.1.0",
            })
            try:
                with self._opener.open(req, timeout=30) as response:
                    payload = response.read(16_777_217)
                    if len(payload) > 16_777_216:
                        raise GitHubError("API response exceeds the size limit")
                    value = json.loads(payload)
                    self.audit.append({"path": path, "params": params or {}, "at": started,
                                       "status": response.status,
                                       "rate_remaining": response.headers.get("X-RateLimit-Remaining")})
                    if not isinstance(value, (dict, list)):
                        raise GitHubError("unexpected API response shape")
                    return value
            except HTTPError as exc:
                self.audit.append({"path": path, "params": params or {}, "at": started, "status": exc.code})
                retry = exc.headers.get("Retry-After")
                if exc.code in (429, 502, 503, 504) or (exc.code == 403 and retry):
                    try:
                        delay = float(retry) if retry else 2 ** attempt
                    except ValueError:
                        delay = 60.0
                    if attempt < 2 and 0 <= delay <= 60:
                        self.sleep(delay)
                        continue
                # Avoid including response bodies, request headers or tokens in exceptions.
                raise GitHubError(f"GitHub returned HTTP {exc.code}; request stopped") from None
            except (URLError, TimeoutError, json.JSONDecodeError, UnicodeError):
                if attempt < 2:
                    self.sleep(2 ** attempt)
                    continue
                raise GitHubError("GitHub request failed; partial collection retained") from None
        raise GitHubError("request retry limit exceeded")


def search_partitioned(client, query: str, *, low: int = 0, high: int = 384_000):
    """Return hits and a per-leaf coverage ledger; never claim index exhaustiveness."""
    pending = [(low, high)]
    hits: dict[tuple, dict] = {}
    ledger = []
    while pending:
        left, right = pending.pop(0)
        q = f"{query} size:{left}..{right}"
        response = client.get("/search/code", {"q": q, "per_page": 100, "page": 1})
        count = response.get("total_count", 0)
        incomplete = bool(response.get("incomplete_results", False))
        if not isinstance(count, int) or count < 0:
            raise GitHubError("invalid code-search count")
        if count > 1000 and left < right:
            mid = (left + right) // 2
            pending[0:0] = [(left, mid), (mid + 1, right)]
            continue
        capped = count > 1000
        fetched = 0
        pages = min(10, (count + 99) // 100)
        for page in range(1, pages + 1):
            result = response if page == 1 else client.get("/search/code", {"q": q, "per_page": 100, "page": page})
            incomplete |= bool(result.get("incomplete_results", False))
            items = result.get("items", [])
            if not isinstance(items, list):
                raise GitHubError("invalid code-search items")
            fetched += len(items)
            for item in items:
                repo = item.get("repository", {})
                # Authenticated search may see private results: discard them at the boundary.
                if repo.get("private") is not False:
                    continue
                key = (repo.get("full_name"), item.get("path"), item.get("sha"))
                if not all(isinstance(x, str) for x in key):
                    continue
                hits[key] = item
        ledger.append({"query": q, "reported_total": count, "fetched": fetched,
                       "api_incomplete": incomplete, "capped": capped,
                       "returned_pages_complete": not incomplete and not capped and fetched == count})
    return list(hits.values()), ledger
