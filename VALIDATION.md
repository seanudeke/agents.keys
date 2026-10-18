# Validation record

Validation date: 2026-10-18 (UTC).

Environment: Python 3.12.14; PyYAML 6.0.3.

Completed:

- 81 offline unit and integration tests passed.
- Local scan, aggregate reporting, and boundary-check CLI paths exercised.
- Search partitioning, capped/incomplete results, budgets, public-only filtering, default-branch snapshots, and retained partial data tested with deterministic API responses.
- HTTP transport authentication, retry, hard-budget, redirect, and sanitized-error handling tested without real credentials or network calls.
- Independent-review identity and agreement handling checked, including identical workflow contents at different locations.
- Trial evidence, hashes, oracle consistency, error denominators, implementation revisions, paired outcomes, and missing measurements checked.
- The Python wheel built successfully.
- The original manuscript copy matches the supplied bytes.
- Source inspection found no matches for the checked GitHub token, AWS access-key, or private-key formats.
- The connected GitHub read API accepted a minimal public code-search request. This was a connectivity check, not study collection.

Not completed:

- Live public-repository mining through the packaged HTTP client.
- Independent reviewer labeling or recall validation.
- Real-provider agent attack replays.
- Docker execution: Docker is unavailable in the preparation environment.
- Remote GitHub CI runs and the Python 3.11/3.13 matrix.
- Independent security review, empirical replication, or manuscript peer review.

The included container command is tested structurally. Its execution and the deployment host's enforcement remain to be checked where Docker is available. The project is a tested research implementation for the documented scope, not a completed empirical study.
