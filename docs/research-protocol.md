# Study protocol

Protocol version: 0.1.0. Freeze the reviewed protocol, catalog, implementation revision, and analysis plan before the main collection. Pilot data can inform a revision but must remain distinguishable from the final study.

## Research questions

1. Among observed eligible agent jobs, how often do untrusted-input indicators, credential references, and declared repository writes coexist?
2. How do those indicators vary by referenced credential category, event, runner label, and game-engine marker?
3. Under explicitly tested runtime boundaries, how do paired baseline and profile configurations differ in attacker success, task success, latency, and token usage?

RQ1 and RQ2 are static configuration questions. RQ3 requires new, independently observable runtime evidence.

## Population and selection

Use one dated collection over the default branches of public, non-fork, non-archived repositories. Record the catalog, search terms, each size partition, API response completeness, request budget, repository budget, collection times, and exclusions.

The collection is an index-derived, nonprobability sample. File-size partitioning addresses the per-query return cap only. It cannot establish full GitHub coverage, recover unindexed files, or freeze a changing search index. Record the exact default-branch commit for each downloaded snapshot.

Default discovery uses the action catalog. A repository can contribute additional recognized CLI jobs once its workflows are collected. Do not claim the discovery frame includes every CLI-only deployment or all hosted review bots.

Units are eligible repositories, workflow files, and jobs containing recognized agent invocations. Each job is counted once per repository snapshot, even if it invokes multiple agents. Agent-category breakdowns overlap.

## Indicators and unknowns

The output fields deliberately avoid equating a parsed flag with a runtime exploit:

| Field | Operational interpretation |
| --- | --- |
| a_input_indicator | Event-authored text is referenced within a recognized agent step; otherwise unknown |
| b_sensitive_indicator | Credential reference or declared OIDC minting opportunity; otherwise unknown |
| c_declared_repository_write | Repository-token write declaration, absent declaration, or unknown inherited/dynamic setting |
| triple_indicator_candidate | All 3 indicators present; a candidate for review, not a confirmed vulnerability |

The input field is an indicator, not whole-program taint tracking. It may include references in a condition rather than the final prompt. Secret names suggest categories, not credential validity or privilege. Non-model and model credentials are both retained. OIDC is reported separately because minting a token does not establish a cloud role's trust policy.

Use the exact labels present, absent, and unknown for their specified static fields. Absence in a declared repository-write field is not absence of every possible effect channel.

## Engine classification

Unity: ProjectSettings/ProjectVersion.txt. Unreal: a .uproject file. Godot: project.godot.

Classification is marker based. Multiple engines may occur in one repository. A truncated tree without a marker has unknown engine status. A marker does not establish that the observed agent job builds that engine, that the project is a commercial studio, or that the organization has limited security staffing.

## Validation

Review a prespecified random sample of observed agent jobs using the versioned codebook. Preserve the seed, sampling frame, original blank sample, two independent label files, adjudication record, and false-positive/false-negative analysis.

A sample from detected jobs estimates classification agreement within that frame. Recall requires an additional sample from excluded or unmatched workflows; do not infer it from agreement alone. The included sampler draws only from detected jobs.

Report disagreements and unknowns. Cohen's kappa is undefined for some degenerate marginal distributions; the tool returns null rather than an invented score.

## Analysis

Keep job-level and repository-level denominators separate. Report counts before percentages. Give missingness and exclusion counts. Use per-engine groups as descriptive subsets; overlapping groups do not sum to a partition.

Do not attach a binomial population-prevalence interval to a nonprobability GitHub index sample. A sensitivity analysis or repository-cluster resampling can describe sample variability if separately specified; it does not repair selection bias.

## Runtime study

Use only owned, dedicated sandbox repositories with canary credentials and approved egress. Freeze the provider/model identifiers, agent/action revision, configuration hashes, tasks, attack variants, repetitions, success criteria, and independent outcome oracle. Randomize or counterbalance condition order. Reset state and caches between independent trials.

Evaluate task utility on clean tasks as well as attacked tasks. A failed run is an error, not a blocked attack. Report adaptive attacker knowledge and tuning budgets. Distinguish credential exfiltration, unauthorized writes, availability failures, and content manipulation.

The supplied trial summarizer verifies recorded evidence and conditional paired statistics. It does not implement a live agent, independently judge maliciousness, or validate provider behavior.
