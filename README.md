# Agents With Keys

Research software for **Agents With Keys: Measuring and Constraining Authority in AI-Enabled CI**, by Osita Sean Keluo-Udeke.

Version 0.1.0 includes bounded workflow scanning, read-only collection, aggregation, independent-review utilities, closed-schema proposal validation, and recorded-trial evidence checks. It does not implement a complete credential gateway, effect service, live model adapter, or prompt-injection defense.

The October 19, 2026 collection selected 300 repositories from 410 index-discovered names and observed 462 agent jobs in 267 repositories, including 48 configuration review candidates. Seven snapshots failed; four were partial because 13 workflow files were rejected. These are descriptive indicators, not confirmed vulnerabilities or population prevalence. Independent labels, recall assessment, and live-agent security evaluation remain outstanding.

## Install and reproduce components

Requires Python 3.11+. The recorded local run used Python 3.12.14 and PyYAML 6.0.3.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/component_study.py --repository . --output runs/components-new
python scripts/source_inventory.py --check
```

Without an editable installation, prefix Python commands with `PYTHONPATH=src` on Unix-like systems. The six test modules contain 90 checks. The component script runs them and reproduces ten boundary cases, replay and semantic-limit probes, three unordered allowed-label sets, scanner illustrations, and a rejected/accepted worked proposal. Receipts do not authorize execution. Use a new output directory for retained runs.

## Collect a new sample

Provide a GitHub token through `AWKEYS_GITHUB_TOKEN` or `GITHUB_TOKEN` in the local environment, never a tracked file or command-line argument. The packaged client makes authenticated GET requests only.

```bash
awkeys collect --search-pages-per-query 1 --max-repositories 300 --max-requests 6000 --output private/new-collection
awkeys summarize private/new-collection/observations.jsonl --manifest private/new-collection/manifest.private.json --output private/new-summary.json
python scripts/analyze_deployment.py private/new-collection --output private/new-analysis.json
```

`mine` remains an alias; `python mine.py` is compatible. Omitting `--search-pages-per-query` uses size-partitioned discovery. REST search uses legacy syntax: public filtering is enforced on returned hits and metadata, rather than the unsupported `is:public` qualifier.

The bounded command intentionally cannot claim complete discovery. Exit status 2 preserves capped or incomplete runs; inspect the manifest. `selected_snapshots_complete` describes selected snapshots separately from search completeness. Failed or rejected files have unknown job counts. Collected project code is never executed.

## Recompute the reported collection

`evidence/deployment-analysis.json` contains all-available counts, a fully analyzed sensitivity subset, collection flow, and commitments to private observations, manifest, and request ledger. `evidence/collection-freeze.json` records initial source digests and the error-handling amendment made during acquisition. The selection plan is `docs/deployment-run-2026-10-19.md`.

The reported acquisition used the authenticated connected GitHub read API to retain responses, then replayed them through the collector. Metadata were projected to required fields; decoded blobs were encoded for replay and checked against Git object IDs. Replay is not a second sample. Capture was 16:32-16:51 UTC on October 19, 2026. A fresh online search produces a new sample.

Exact recomputation requires the separately controlled snapshot/response bundle from the author:

```bash
awkeys collect --response-cache /path/to/discovery-cache --search-pages-per-query 1 --max-repositories 300 --max-requests 6000 --output private/recomputed
python scripts/analyze_deployment.py private/recomputed --output private/recomputed-analysis.json
```

Compare aggregate counts and workflow digests. Per-run identifiers and replay timestamps differ. Public commitments identify the original files, not a claim that later manifests are byte-identical. Identities, workflow source, salts, and logs are not released in Git.

## Independent review and runtime evidence

```bash
awkeys validation-sample private/recomputed/observations.jsonl --count 100 --seed 20261019 --output private/blank-review.csv
awkeys agreement private/reviewer-a.csv private/reviewer-b.csv --output private/agreement.json
awkeys evaluate private/trials.jsonl --evidence-root private/evidence --output private/trial-summary.json
```

Two human reviewers must label independently before adjudication. Tools do not supply judgments. Runtime evidence requires actual execution and independent outcome oracles. The optional Docker component harness in `evaluation/README.md` was not executed in the preparation environment.

## Release and manuscript

The release is `v0.1.0`. `source_inventory.txt` hashes every other tracked regular file, excluding itself. After merging to `main`, regenerate and commit the inventory, then read `git rev-parse HEAD` for the manuscript pin. The manuscript build accepts that final commit as an external argument, avoiding a self-referential commit hash inside a committed file.

See `paper/README.md` for the manuscript and figure build. Historical drafts are preserved separately and are not evidence for current findings. `VALIDATION.md` states verification scope. `.zenodo.json` prepares deposit metadata; no DOI is claimed until publication.
