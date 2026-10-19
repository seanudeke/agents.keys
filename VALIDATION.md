# Validation record

Local verification: October 19, 2026; Python 3.12.14, PyYAML 6.0.3.

- All 90 offline tests passed. Nine new checks cover bounded discovery, REST syntax, public-hit filtering, distinct search/snapshot completeness, recorded-response provenance and tamper rejection, and continued collection after a failed workflow blob.
- Ten deterministic validator cases matched expectations: one within-policy proposal accepted and nine rejected. Valid input remains replayable; a permitted label can violate the task oracle. These are component observations, not attack rates.
- The worked example rejects an outside-policy label and accepts the repaired proposal; execution authorization remains false.
- The deployment collection selected 300 eligible public repositories: 289 fully analyzed, four partial, seven unresolved. All 2,915 retained workflow blobs matched Git object IDs; bounded parsing rejected 13.
- Aggregation produced 462 recognized jobs and 48 review candidates; the fully analyzed subset contains 452 jobs and 46 candidates. Denominators and unknowns appear in `evidence/deployment-analysis.json`.
- Acquisition used the connected GitHub read API and recorded-response replay. No live run through the packaged local-token HTTP client is claimed; that transport is checked offline.
- The manuscript and figure were rebuilt from source. The delivered review notes record final Word/PDF checks.
- GitHub Actions runs Python 3.11, 3.12, and 3.13. Consult Actions for results at the exact reviewed/released commit; configuration alone is not a passing run.

Not completed: independent labels or recall validation, live-provider attacks, complete credential/effect mediation, external artifact evaluation or peer review, or Docker execution. A DOI requires authenticated publication. Passing software checks are not security guarantees.
