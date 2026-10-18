# Evaluation workflow

There are three distinct layers:

1. **In-memory validator checks:** executable with awkeys boundary-checks. No model, network, GitHub write, or real credential is involved.
2. **Offline container component checks:** scripts/run_boundary_container.py runs the same validator inside a constrained container. Docker and a locally available immutable Python image are required.
3. **Recorded live-agent evaluation:** awkeys evaluate verifies and summarizes records produced by an actual controlled agent runner. Provider adapters and live attack runs remain separate research work.

## Optional container check

Select a trusted Python 3.11+ image, resolve its exact digest, and make it available locally. The harness refuses mutable tags and does not pull an image.

    python scripts/run_boundary_container.py --image IMAGE_AT_SHA256_DIGEST --output runs/container-component-checks.json

Replace IMAGE_AT_SHA256_DIGEST with an actual image reference of the form image@sha256:64-hex-digits. The harness mounts a temporary directory containing only broker.py. It does not mount this repository, the Docker socket, host home directories, credentials, run data, or collected source.

Network is disabled, the root filesystem is read-only, capabilities are dropped, privilege escalation is disabled, and memory/CPU/process limits are set. These options require verification on the deployment host. A passing component check does not establish all security properties of a live agent architecture.

## Live trial contract

Each JSONL row must have exactly:

    record_kind, trial_id, protocol_sha256, corpus_sha256, configuration_sha256,
    provider, model, agent_version, action_sha, task_id, attack_id, repetition,
    variant, started_at, status, attacker_success, task_success,
    elapsed_seconds, input_tokens, output_tokens, evidence

Requirements:

- record_kind is agent_trial; variant is baseline or profile.
- started_at is an ISO timestamp with a timezone.
- The action revision is a 40-character commit SHA.
- Protocol, corpus and configuration fields are SHA-256 values matching evidence files.
- A completed trial has Boolean attacker_success and task_success.
- An errored trial has null outcomes. It contributes to the error denominator.
- elapsed_seconds is an actual finite nonnegative observation.
- Missing token measurements are null, never zero substitutes.
- evidence lists relative paths, SHA-256 values and roles.
- Every trial has execution_log, protocol, corpus and configuration evidence.
- Completed trials additionally have outcome_oracle evidence.
- The oracle is JSON containing matching Boolean attacker_success and task_success values.

Evidence must stay inside the specified directory; symlinks cannot escape it. Hash verification establishes consistency with the supplied files, not that a measurement or oracle is truthful.

Pair conditions by provider, model, task, attack, and repetition. Keep the agent/action revision constant. Analyze changes of protocol, corpus, implementation, and configuration in separate cohorts.

## Before live execution

Use only dedicated repositories you own. Use synthetic canaries instead of real release credentials or private source. Establish an enforced agent boundary, a separately trusted effect validator, exact target binding, a state-reset procedure, a scoped egress destination, provider spend limits, and independent task/attack oracles.

The fixture checks do not include executable exploit payloads. Published attack classes need source verification, authorized adaptation, and a frozen test design before evaluation. Never replay them against a mined project.
