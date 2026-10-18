# Release and submission gates

Implementation gates:

- Offline unit and CLI integration tests pass.
- Direct CI actions are pinned to reviewed immutable revisions.
- No credentials, raw snapshots, identifying findings, environment files, or run outputs are tracked.
- Dependency versions and catalog changes are recorded.
- Document which commands require GitHub authentication or Docker.

Study gates:

- Freeze the protocol and implementation before the main run.
- Inspect every incomplete search, truncated tree, parser exclusion, budget stop, and empty group.
- Complete independent validation and a separate recall analysis if claimed.
- Run actual baseline/profile agent trials using dedicated owned sandboxes and canaries.
- Preserve execution evidence, model/action versions, success oracles, and error outcomes.
- Audit exported aggregates for identifying small cells.
- Complete any required disclosure before naming a vulnerable project.

Paper gates:

- Every reported number traces to a reproducible artifact and denominator.
- Component fixtures are excluded from empirical tables.
- Claims match runtime enforcement actually implemented and tested.
- Related-work novelty and source metadata are verified.
- Artifact URL resolves to the intended release.
- Authors, affiliations, funding, contributions, acknowledgments, and required generative-content disclosures are accurate.
- The paper meets the current venue format and page limit.

Passing software tests does not satisfy the study or paper gates.
