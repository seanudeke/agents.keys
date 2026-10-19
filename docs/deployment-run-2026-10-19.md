# Bounded deployment collection: 2026-10-19

This plan was fixed after query calibration and before the analytic collection.
It is not a registered study. The pilot and calibration queries are not analytic observations.

- Use the unchanged five-action seed catalog and the reviewed scanner.
- For each distinct, lexically sorted action query, request the first 100 REST
  code-search results in the default best-match order, without `is:public`.
  The REST endpoint uses legacy search syntax. Retain reported totals and
  `incomplete_results`; the first page is a budgeted selection, not complete discovery.
- Discard non-public search hits, deduplicate repository names, sort them, and
  attempt the first 300 repositories. Record any repository-cap exclusion.
- Confirm public, non-fork, non-archived eligibility from repository metadata.
  Resolve the default branch to an immutable commit and enumerate its tree.
  Download every top-level workflow YAML blob at that snapshot as read-only data.
- Use a maximum of 6,000 recorded API reads. Retain failures and incomplete trees.
  Do not execute project code, resolve transitive programs, or test third-party attacks.
- Transport for this run: authenticated connected GitHub read API; its returned
  metadata are normalized to the fields consumed by the collector. Decoded blob
  text is re-encoded as base64 and checked against the Git object ID. Responses,
  timestamps, content digests, workflow bytes, and identity mappings stay private.
  A recorded-response client then runs the same collection and reporting logic.
  Replay is explicitly identified; it is not a second network sample.
- Report discovered names, attempted/excluded/failed/analyzed repositories,
  workflow files, recognized jobs, three-valued indicators, action families,
  overlapping credential categories, direct action uses, and engine marker subsets.
  Do not impute unknown fields, attach population prevalence intervals, or call
  candidates vulnerabilities. No independent labeling or recall estimate is claimed.
- Release only aggregate counts, the plan, component evidence, and digest
  commitments. Request controlled access for source snapshots if artifact review
  requires them. Rerunning discovery later is a new sample, not exact replication.

Selection biases include the seed catalog, GitHub indexing and ranking, its
default fork-search behavior, path substring matches, lexical repository cap,
repository clustering, non-simultaneous snapshot retrieval, and unobserved
private, CLI-only, or hosted-service deployments.
