# Real-data demonstration run (Oct 19, 2026)

**What this is:** your scanner and `reporting.summarize`, unchanged, run over real public
repositories that genuinely invoke a catalogued agent action in a workflow. It is a
**small, hand-verified convenience sample, not a census** — so it carries no prevalence
claim. It exists to show the pipeline runs end-to-end on live data and to surface what the
indicators actually look like in the wild.

**Method variant (documented honestly):** discovery was done with a public code index
(grep.app) because this environment blocks the GitHub code-search and blob APIs your
`collect()` uses; snapshots were taken by anonymous blobless `git clone` instead of API
blob reads. Fork/archived exclusion (which `collect()` does from repo metadata) was **not**
applied. Scripts: `scan_one.py`, `summarize_only.py`.

## Sample

10 repositories attempted, 9 had ≥1 catalogued agent job (one, `mercury-invoicing-mcp`,
uses a workflow the seed catalog does not match → 0 jobs, correctly). Agents seen: codex
(18 jobs), qodo/pr-agent (6). **Zero** game-engine repos in this sample. Repos:
cloudflare_temp_email, sqle, forms-flow-ai, python-uv, AetherLink, ccs, astral-sh/uv (10
agent jobs), openclaw/openclaw (4), openai/codex (4).

## Numbers (denominator = 24 agent jobs unless noted)

| Measure | Result |
|---|---|
| Repos with ≥1 agent job | 9 / 10 attempted |
| Agent jobs | 24 |
| B — sensitive access present | **24 / 24 (100%)** |
| C — declared repository write present | **7 / 24 (29%)** |
| A — explicit event-text reference in agent step present | **1 / 24**; unknown 23 / 24 |
| **Triple-indicator candidates (A∧B∧C all "present")** | **0 / 24 (0%)** |
| Model-key reference | 23 / 24 (96%) |
| Non-model secret reference (registry/repo, other) | 14 / 24 (58%) |
| Self-hosted runner | 1 / 24 (4%) |
| Unpinned direct remote action uses | 9 / 77 (12%) |
| Secret categories | model 23, registry_or_repository 12, other 3 |

## The honest headline is a methodological finding, not a scare number

The confirmed triple-indicator rate is **0%** — and that is the point, not a
disappointment. The scanner only marks input "present" when an agent step literally
interpolates `github.event.*.body/title` (etc.); a mere untrusted *trigger* is recorded as
an opportunity, not as a confirmed prompt flow. So 23 of 24 jobs sit in the **"unknown"**
input bucket. Meanwhile the dangerous *ingredients* are common: every agent job holds
sensitive access, 29% also carry a write-capable token, and 58% carry a non-model secret
beyond the model key — frequently on workflows triggered by untrusted events.

That is exactly the paper's thesis, now shown on real repositories: **you cannot read true
authority (or vulnerability prevalence) off static YAML.** The ingredients are widespread;
confirming the exploitable combination requires the runtime study. This run validates the
measurement contract on live data and demonstrates the indicators' conservatism — it does
**not** estimate how common real exposure is, and it says nothing game-specific.

## What this does NOT support

- It is **not** a prevalence estimate (tiny, non-random, hand-picked sample; no fork
  exclusion; `population_prevalence_confidence_interval` is deliberately null).
- It does **not** establish national-scale importance; n=24 can't.
- It has **no** game-engine data; that subset was empty here.

## To turn this into a real census

Run your own `awkeys collect` (via `mine.py`) on a machine with a GitHub token. It does the
discovery and exclusion correctly (code-search partitioning, fork/archived filtering,
honest denominators) and will produce a defensible sample size. This demonstration is the
proof the downstream analysis works; the token-run produces the numbers a reviewer will
weigh.
