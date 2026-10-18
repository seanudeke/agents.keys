# Data handling and provenance

Each collection writes:

| Artifact | Contents | Handling |
| --- | --- | --- |
| manifest.private.json | Repository names, snapshot commits, selection, exclusions and errors | Keep private |
| requests.private.json | API paths, queries, status and collection times; no authorization headers | Keep private |
| identity-salt.bin | Random HMAC salt used for repository identifiers | Keep private; restrictive permissions |
| raw/ | Exact public workflow bytes indexed by SHA-256 | Keep private pending disclosure review |
| observations.jsonl | Job indicators, credential names, hashes, workflow paths and pseudonymous repository IDs | Keep private |
| catalog.json | The exact discovery/detection catalog used | Suitable for release after review |
| aggregate.json | Counts and denominators without source identifiers | Review small cells before public release |

Runs, private material, raw data, credentials, and result directories are ignored by Git. A private repository is an additional protection, not a replacement for those exclusions.

HMAC identifiers are pseudonyms. Publishing the salt, raw workflows, or source paths alongside findings can enable reidentification. Do not describe an identifying dataset as anonymous.

Each run uses a different salt. Do not concatenate observations from separate runs: the same project would have different identifiers and could be counted twice. Analyze one frozen collection at a time.

Snapshot commits and content hashes support reproducibility. Restricted access to the source-to-result mapping may still be needed for independent replication. Specify the access procedure and reasons for withholding identities in the submitted paper.

Do not print, validate, use, or publish any credential value found in public source. Record names and categories only. If a workflow contains a suspected hardcoded secret, keep the raw snapshot restricted and follow the disclosure process.

The collector never executes repository code, retrieves secret values, or tests vulnerabilities against collected projects. A scanner flag alone does not justify describing a project as compromised or exploitable.
