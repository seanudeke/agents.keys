# Agents With Keys

Research software for **Agents With Keys: AI Coding Agents, Credentials, and State in CI Pipelines**.

Author: Osita Sean Keluo-Udeke.

This repository contains a working configuration scanner, a read-only GitHub mining pipeline, aggregate reporting, independent-review tools, a closed-schema proposal validator, and an evidence-checking harness for recorded agent trials.

**Research status:** implementation and component checks. The public-repository study, independent manual validation, and live-agent attack evaluation have not been completed. No fixture result is a finding for the paper.

## Start locally

Requires Python 3.11 or newer.

    python -m venv .venv
    . .venv/bin/activate
    python -m pip install -r requirements.txt
    python -m pip install -e .
    python -m unittest discover -s tests -v
    awkeys --help

On Windows, activate with .venv\Scripts\activate. Alternatively, without an editable installation, use PYTHONPATH=src python -m awkeys on Unix-like systems.

Scan a local repository without executing its code:

    awkeys scan /path/to/repository --output runs/local/observations.jsonl
    awkeys summarize runs/local/observations.jsonl --output runs/local/summary.json
    awkeys boundary-checks --output runs/component-checks.json

The summary reports jobs and repositories with separate denominators. Unknown configurations remain unknown. Missing engine markers on an incomplete tree do not become a non-game classification.

## Collect public workflow snapshots

Make a GitHub token available as AWKEYS_GITHUB_TOKEN or GITHUB_TOKEN through your local credential environment. Do not put credentials in configuration files, commit them, or pass them as command-line arguments. The collector uses authenticated GET requests only.

    awkeys mine --output runs/pilot-20261018 --max-repositories 25 --max-requests 300

The compatible manuscript entry point is:

    python mine.py --output runs/pilot-20261018 --max-repositories 25 --max-requests 300

For a fixed repository list, put one owner/repository per line in a local text file:

    awkeys mine --repositories private/repositories.txt --output runs/fixed-sample --max-repositories 100
    awkeys summarize runs/fixed-sample/observations.jsonl --manifest runs/fixed-sample/manifest.private.json --output runs/fixed-sample/aggregate.json

Every run requires a new empty output directory. Request and repository budgets are explicit. An interrupted, capped, malformed, or truncated collection exits with status 2 and preserves its partial artifacts. It must not be described as a complete census.

The default discovery catalog searches action invocations. Direct CLI invocations are additionally recognized in the collected repositories. CLI-only repositories outside this discovery frame, hosted bots without workflows, private projects, forks, and archived repositories are outside the default eligible sample.

## Independent configuration review

    awkeys validation-sample runs/fixed-sample/observations.jsonl --count 100 --seed 20261018 --output private/review-sample.csv
    awkeys agreement private/reviewer-a.csv private/reviewer-b.csv --output private/agreement.json

Give two reviewers separate copies of the blank sample and the private snapshot lookup. They label independently before adjudication. The software calculates agreement; it does not create reviewer judgments. See docs/review-codebook.md.

## Evaluation

The included output validator accepts only bounded label proposals bound to a trusted repository, issue, run, and source revision. It does not apply GitHub changes or establish a complete agent sandbox.

The default component checks use in-memory fixtures:

    awkeys boundary-checks --output runs/boundary-checks.json

An optional Docker harness mounts only the validator code, uses an immutable local Python image, and disables network access. Read evaluation/README.md before running it.

Real-agent trial records require hashed execution logs, a separate outcome oracle, the frozen protocol, task corpus, and tested configuration:

    awkeys evaluate private/trials.jsonl --evidence-root private/evidence --output runs/evaluation-summary.json

The evaluator rejects fixture records, missing or changed evidence, unpaired duplicates, mixed implementation revisions, and errors reported as successful defenses. No model adapter or live-agent outcome is silently substituted for a missing experiment.

## Repository contents

| Location | Purpose |
| --- | --- |
| src/awkeys/scanner.py | Safe YAML parsing and configuration indicators |
| src/awkeys/catalog.json | Reviewed seed action catalog and heuristic CLI rules |
| src/awkeys/github.py | Authenticated read-only requests and search-cap ledger |
| src/awkeys/mining.py | Public default-branch snapshots, exclusions, raw provenance |
| src/awkeys/reporting.py | Aggregate counts, review sampling, agreement |
| src/awkeys/broker.py | Closed-schema example output validation |
| src/awkeys/evaluation.py | Recorded-trial evidence checks and paired summaries |
| scripts/run_boundary_container.py | Offline Docker component harness |
| docs/ | Protocol, limitations, codebook, profile, provenance, release gates |
| examples/ | Inert configuration examples; never used as research findings |
| paper/ | Original supplied draft and its evidence requirements |
| tests/ | Offline unit and integration tests |

## Interpretation limits

- Configuration references do not establish that a credential was available at runtime.
- An inherited token default is unknown unless independently verified.
- A read-only repository token does not establish that network egress is blocked.
- Model credentials remain credentials.
- A self-hosted label does not establish that a runner is persistent.
- A full commit pin limits reference movement. It does not establish that action code is safe.
- Stage separation still requires validation of untrusted outputs and exact target binding.
- Neither this scanner nor its component tests proves that a model resists prompt injection.

The evidence and assumptions that must change in the manuscript are mapped in docs/manuscript-evidence-map.md. See docs/research-protocol.md before collecting publication data.
