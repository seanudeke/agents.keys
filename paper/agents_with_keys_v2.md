# Agents With Keys: Measuring and Constraining Authority in AI-Enabled CI

Osita Sean Keluo-Udeke

> Revision v2 (2026-10-19). Supersedes the v0.1 scaffold in `DRAFT_agents_with_keys.md` and the prior revised manuscript. This revision adds an illustrative run on public repositories (Section 5.3), reflects that the implementation repository is now public, and records reference verification. It remains a research-method-and-prototype paper: no population prevalence and no live-agent defense result are claimed.

## Abstract

AI coding agents extend continuous integration with natural language decisions and tool use, while inheriting an execution environment designed for deterministic automation. A workflow can consequently combine contributor-controlled text, sensitive credentials, and channels that alter repository or release state. Assessing that combination requires separating visible configuration from effective runtime authority. We present Agents With Keys, a framework that connects three-valued configuration indicators to an eight-control least-privilege profile and an evidence protocol for evaluating it. The accompanying prototype implements bounded workflow parsing, versioned agent discovery, immutable repository snapshots, aggregate reporting, a narrowly scoped output validator, and integrity checks for recorded trials. All 81 offline regression tests passed; ten deterministic validator checks matched their expected outcomes. A first run over nine public repositories (24 agent jobs) exercises the collection and reporting path on live configuration: every agent job referenced sensitive access and a minority declared a repository write, yet none met the strict three-indicator definition — an illustrative, non-random sample, not a prevalence estimate. Two additional probes demonstrate the limits of this evidence: a valid proposal remains replayable, and an allowed label can still be wrong for its task. These observations support component behavior, not population prevalence or resistance to model-mediated attacks. We specify a separate deployment study and paired live-agent evaluation, with explicit denominators, independent outcome oracles, and treatment of errors. The framework provides a reproducible basis for studying CI authority without treating configuration hints or passing software tests as security guarantees.

Keywords: agentic engineering, continuous integration, prompt injection, least privilege, software supply chain

## 1 Introduction

An automated issue-triage agent seems distant from a release-signing system. On a shared CI runner, however, the distance between them depends on credentials, filesystem access, network paths, and downstream jobs. An injected issue description need not defeat the model's reasoning if the surrounding workflow already gives the agent a route to a sensitive effect. Conversely, an alarming YAML fragment does not establish that a usable credential or attacker-reachable execution path exists.

Prior research has established that this is a substantive attack surface. TaintAWI analyzes flows from GitHub event data into agent prompts and downstream sinks [1]. GitInject exercises attacks in live, isolated GitHub workflows and examines workflow-level countermeasures [2]. We build on this work by connecting what an audit observes, what an enforcement mechanism actually controls, and what an experiment can legitimately conclude.

Meta's Agents Rule of Two identifies the combination of untrusted input, sensitive access, and state change or external communication as requiring particular caution. Where all three are necessary, its guidance calls for supervision or reliable validation [3]. Translating that guidance into CI is difficult because a GitHub job is not necessarily one isolated agent session, a read-only repository token does not eliminate network effects, and a second job can still execute an unsafe model-derived proposal.

This paper contributes three things. First, it defines an auditable measurement contract that preserves unknowns and distinguishes credential references from effective authority. Second, it specifies eight controls as enforcement obligations, including the assumptions needed for bounded effects. Third, it provides a tested prototype, reports deterministic component observations and an illustrative run of the collection and reporting path on public repositories, and specifies a protocol for the deployment and live-agent studies that remain necessary. The contribution is a research method and prototype; it is not a completed census, a replacement for taint analysis, or a demonstrated defense against published attacks.

## 2 Background and related work

### 2.1 CI authority and agent workflows

GitHub Actions executes workflow jobs with event-dependent tokens, optional secrets, and runner resources. Declared token permissions can be overridden at job scope; effective permissions also depend on repository settings and event policy [4]. OIDC permission permits requesting an identity token, but does not by itself authorize a cloud resource operation [5]. An agent can also acquire authority through application tokens, checkout credentials, subprocesses, mounted files, tool servers, or a later workflow that trusts its artifacts. The relevant object of analysis is therefore an authority path, not only a token declaration.

Koishybayev et al. examined CI admission, execution, code, and secret access before the present agent ecosystem [6]. Their historical findings motivate permission analysis, but cannot be reused as contemporary agent-deployment estimates. SLSA v1.2 specifies isolation and protection of provenance-signing material at its higher build level [7]. Those requirements concern build integrity; conforming provenance does not establish that an agent's review or proposed patch is correct.

### 2.2 Injection analysis and enforcement

TaintAWI models prompt-to-agent and prompt-to-script injection and analyzes invocation guards, derived outputs, and security-sensitive sinks [1]. GitInject studies actual CI execution semantics, including configuration files, credential handling, and infrastructure boundaries [2]. Our scanner has a substantially narrower role: it records reviewable configuration indicators without attempting comparable interprocedural taint analysis or exploit confirmation.

CaMeL separates control and data flow and mediates capabilities [8]. Progent represents privileges as policies over tool calls and constrains policy expansion [9]. GitHub Agentic Workflows combines isolation, mediated credentials, constrained outputs, and logging [10]; its implementation is publicly available under an MIT license [11]. Our profile organizes enforcement and measurement requirements across existing workflows, while the prototype implements only selected components. Comparative security and performance evaluation against these systems remains future work.

## 3 Threat model and measurement contract

### 3.1 Attacker and trusted components

The attacker can contribute text or files through an issue, comment, pull request, or another input consumed by an agent. The attacker initially lacks valid target credentials and permission to change the trusted default-branch workflow. We consider unauthorized disclosure, repository or release mutation, persistent influence, and manipulation of legitimate task outcomes. The model may follow injected instructions; the security argument does not depend on reliable refusal.

The proposed enforcement design trusts the CI control plane, isolation substrate, credential service, effect service, and reviewed policy. An attacker may control the proposal these components receive. Compromise of a trusted component is outside the conditional argument, but remains relevant to deployment review. A job boundary counts as a security boundary only when shared state, credentials, and communication paths are separately constrained. Neither successful parsing nor a provider's tool-setting label demonstrates that isolation.

### 3.2 Three static indicators

For each recognized agent job, the scanner records the fields in Table 1. These are operational definitions for the artifact, not direct measurements of the three runtime properties in the Rule of Two. The input indicator recognizes event-text expressions within an agent step; because that search includes conditions and environment fields, a match need not be a prompt flow. The sensitive-access indicator includes model-key references and declared OIDC minting opportunities. It does not establish that the referenced secret exists or is reachable by the agent process.

**Table 1. Configuration indicators and their interpretation**

| Field | Present | Absent or unknown |
|---|---|---|
| Input indicator | Recognized event-text expression in an agent step | Otherwise unknown; indirect input flow is unresolved |
| Sensitive indicator | Visible secret reference or declared OIDC minting opportunity | Otherwise unknown; runtime reachability is unresolved |
| Declared repository write | Explicit token write declaration other than OIDC | Absent for an explicit declaration without such writes; unknown for inherited or dynamic values |

A job with all three indicators present is a review candidate. It is not a confirmed vulnerability. A negative candidate flag is also not a clean bill of health: its input or credential field may be unknown, another credential may grant writes, or external communication may remain available. The scanner reports egress enforcement, actor-gate correctness, tool enforcement, and runner ephemerality as unresolved unless established separately. A self-hosted label alone is not evidence of persistence.

### 3.3 Separating declarations from capability

Consider three constructed issue-triage workflows. Each references the issue body in an agent step. With a model-key reference and issues: write, all three indicators are present. Changing the declaration to contents: read makes the repository-write indicator absent, but leaves egress unknown. Removing the visible key reference changes the sensitive indicator to unknown, not absent. These exact outputs are reproduced by the component study. The examples expose an interpretation hazard: removing a YAML expression can remove evidence without removing authority.

The unit of static reporting is one job in one workflow path at one repository snapshot. Multiple agent invocations within that job do not create independent jobs. Identical file contents at different paths remain different observations. Agent-family and engine-marker groups can overlap, so their counts are not a partition of the sample.

## 4 Least privilege as an enforcement contract

Figure 1 separates untrusted reasoning from trusted credential and effect mediation. The eight controls below describe a target architecture. They are not eight YAML switches, and the prototype does not implement the complete architecture.

*Figure 1. Proposed trust boundaries for agent execution and effects. Dashed boxes describe proposed trusted services. The prototype implements the closed-schema validator only.*

### 4.1 Credential and token boundaries

P1 Credential separation. Release, signing, store, cloud, and long-lived repository credentials must remain outside agent-reachable memory, environment variables, files, and tool responses. A model API key is also sensitive. Where remote inference is required, a separate gateway can hold the provider credential and enforce destination, request, and spending limits. The gateway, its logs, and any returned data become part of the trusted computing base. Merely omitting the key from a prompt is insufficient.

P2 Token minimization. Begin with no token permissions and grant the smallest explicit job-level set required for reading. Evaluate alternate application tokens, persistent checkout authentication, OIDC trust, and service credentials separately. A declaration such as contents: read constrains that token channel; it does not prohibit a subprocess from sending data over the network. OIDC should be authorized only where a separately reviewed task and cloud trust policy require it.

### 4.2 Effects and execution state

P3 Vetted effects. The agent emits an untrusted proposal, not an executable script. A trusted service validates a closed schema, allowed operation, target repository and object, originating run, immutable source revision, size limits, and task authorization. It must also enforce freshness, replay policy, and any required approval before using a narrowly scoped credential. It must not load code, policy, or executables from the proposal's untrusted workspace. Moving a shell command into a later job merely relocates the injection sink.

P4 Fresh execution. Provision a fresh environment for each independent run and prevent influence through workspaces, processes, sockets, writable mounts, caches, and reusable artifacts. Record the actual lifecycle and cache producers rather than inferring them from runner labels. SLSA's isolation requirements provide a relevant baseline [7], but do not establish the correctness of a particular agent deployment. Only explicitly accepted, provenance-bound outputs may cross into later trusted work.

### 4.3 Input, tools, dependencies and communication

P5 Input boundaries. Use trusted workflow and policy revisions. Keep contributor text and repository-supplied agent instruction files outside operator authority, including when the event was initiated by a maintainer. Validate who can trigger the job and which revision is checked out. GitHub's June 2026 checkout changes refuse specified fork-head patterns in privileged contexts, with version-dependent coverage and opt-outs [12]. They do not establish that all remaining files or prompts are trustworthy.

P6 Tool mediation. Authorize typed operations and argument arrays at an enforcement point the agent cannot bypass. A shell allowlist is ineffective if another tool exposes an interpreter, equivalent filesystem access, or an unrestricted network client. Re-parsing a command can reveal structure but does not safely implement a complete shell policy. Where practical, replace general shell authority with specific read or transformation capabilities and verify that alternate paths are unavailable.

P7 Dependency immutability. Review dependency behavior and bind execution to approved revisions. GitHub's workflow lockfiles, in public preview at the preparation date, record action commits and source repository identities, including specified transitive dependencies; reusable workflow dependencies have separate lockfile scope [13]. Where lockfiles are unavailable, direct full-commit pins and image digests remain useful controls [14]. Neither mechanism certifies benign behavior or freezes every dependency downloaded by action code. The prototype records direct pin syntax; it does not resolve lockfile or transitive execution semantics.

P8 Egress and audit. Enforce outbound policy outside the agent's control, including tool servers and provider gateways. Approved destinations can still carry attacker-selected data, so destination filtering alone is not a confidentiality proof. Retain protected, redacted evidence of tool calls, authorization decisions, effects, and failures. Logs must not become a secondary secret-disclosure channel. GitHub's June 2026 cache-token restrictions also affect specific cross-trust persistence paths and must be recorded when reproducing earlier attacks [15].

### 4.4 A conditional argument for bounded effects

Assume that every externally visible mutation from the agent sandbox is mediated by a trusted effect service; the service's policy and context cannot be changed by the agent; and the service executes only an authorized operation after validating its target, revision, bounds, and freshness. Under those assumptions, an execution trace cannot contain an unmediated mutation or a mutation outside that policy. To see this, consider the first alleged violating mutation. Complete mediation requires it to pass through the service, while correct enforcement requires the service to reject it, contradicting its execution.

This is a conditional architectural argument, not a formal verification result. It does not prove confidentiality, model alignment, semantic correctness, or the completeness of mediation in an implementation. For example, a malicious but schema-valid label can remain within policy. Patch generation requires a richer authorization decision than the label example, and release signing must not become an automatic consequence of receiving syntactically valid agent output.

## 5 Prototype and component observations

### 5.1 Implementation

The Python prototype has five connected functions: scan configuration, collect public snapshots, summarize indicators, validate bounded proposals, and validate recorded trial evidence. Its seed catalog contains five action references representing four families, including a legacy Qodo alias, plus five heuristic CLI rules. CLI rules can recognize additional jobs in collected repositories; action-based discovery does not cover the population of CLI-only deployments. Hosted review services without an observable workflow invocation are outside this frame.

Parsing is read-only and bounded to one MiB, 30,000 YAML events, 100 aliases, and a nesting limit. It preserves the on key, rejects unsafe tags, conflicting duplicate keys, recursive aliases, and unsupported document structures, and reports exclusions. It does not execute mined code, resolve arbitrary reusable workflows, expand every matrix, or analyze transitive shell behavior. Credential categories are name-based hypotheses. Both inherited authority and ambiguous references remain visible as uncertainty.

The collector records a catalog digest, query ledger, exact default-branch commit, source hashes, tree completeness, exclusions, and explicit request and repository budgets. Its read-only HTTP client bounds retries and prevents authenticated redirects to another destination. Search partitioning addresses the per-query return cap, not index coverage or a changing search population [16]. Per-run keyed repository identifiers reduce casual linkage; they do not make sensitive raw snapshots anonymous. Raw data and identity mappings require separate access control.

### 5.2 Completed validation

On October 18, 2026, all 81 offline regression tests passed in Python 3.12.14 with PyYAML 6.0.3. The five modules contain 29 scanner tests, 22 collection and reporting tests, 21 validator and trial-evidence tests, five HTTP-client tests, and four CLI tests. Their fixtures cover malformed inputs, unknown permissions, capped collection, separate denominators, incomplete evidence, and errors that must not become successful defenses. These counts describe software checks, not independent samples of workflows or attacks.

The deterministic validator exercise contains ten cases. One authorized label proposal was accepted, while nine proposals involving target confusion, an unauthorized operation, an extra field, arbitrary label content, excess labels, or a Boolean issue number were rejected. Table 2 groups the exact observations. No model, live credential, repository mutation, or network attack was involved. Consequently, ten matching outcomes cannot be reported as a prompt-injection block rate.

**Table 2. Deterministic output validator observations**

| Constructed input group | Cases | Expected | Observed |
|---|---|---|---|
| Authorized bounded label | 1 | Accept | 1 accepted |
| Repository issue run or revision mismatch | 4 | Reject | 4 rejected |
| Unauthorized operation or extra field | 2 | Reject | 2 rejected |
| Invalid label content or count | 2 | Reject | 2 rejected |
| Boolean issue identifier | 1 | Reject | 1 rejected |

Two additional probes delimit the result. Repeating the same valid proposal twice produced two accepted, identical receipts: the stateless validator does not implement replay protection. A proposal for documentation also passed when the constructed task oracle required needs-triage: schema acceptance did not establish task correctness. Exhausting the nonempty subsets of the two allowed labels produced three accepted label sets. This is a small, intentionally bounded capability, not a general patch or release authorization mechanism. The returned receipt explicitly does not authorize execution.

The recorded-trial validator rejects fixture records, missing or changed evidence, mismatched outcome files, duplicate paired conditions, and incompatible implementation revisions. Its hashes establish byte integrity relative to supplied records; an experimenter can still supply an invalid oracle or misleading log. The optional Docker command constrains a validator component, not an Internet-connected agent. Docker execution and the complete credential and effect services were not evaluated in this study.

### 5.3 Illustrative run on public repositories

To exercise the collection and reporting path on live configuration rather than on offline fixtures alone, we ran the scanner and the aggregation routine, unchanged, over a small set of public repositories whose workflow files genuinely invoke a catalogued agent action. This run substitutes the fetch layer only, for environment reasons: discovery used a public code-search index (grep.app) because the authenticated GitHub code-search and blob endpoints the collector relies on were unavailable, and each repository was snapshotted by anonymous shallow clone rather than API blob reads. Because that index matches substrings rather than `uses:` step semantics, its high-volume results are dominated by source mirrors of the agent tools themselves; candidate repositories were therefore hand-verified to contain a real agent invocation in a workflow file. Fork and archived exclusion, which the collector applies from repository metadata, was not applied. This is an illustrative convenience sample. It is explicitly not the deployment study of Section 6.1, and it carries no prevalence estimate, confidence interval, or game-engine claim.

Ten repositories were attempted; nine contained at least one catalogued agent job, yielding 24 agent-job observations (eighteen identifying a Codex action, six a Qodo/pr-agent action). None carried a game-engine marker. Table 3 reports the aggregate indicators the summarizer emits; denominators are agent jobs unless noted.

**Table 3. Illustrative run (9 public repositories, 24 agent jobs). Indicators, not confirmed vulnerabilities.**

| Measure | Observation |
|---|---|
| Agent jobs (repositories with ≥1 agent job) | 24 (9 of 10 attempted) |
| B — sensitive-access indicator present | 24 / 24 |
| C — declared repository-write indicator present | 7 / 24 |
| A — event-text reference in an agent step present | 1 / 24 (23 unknown) |
| Three-indicator review candidates (A ∧ B ∧ C present) | 0 / 24 |
| Model-key reference | 23 / 24 |
| Non-model secret reference | 14 / 24 |
| Secret categories (jobs) | model 23, registry/repository 12, other 3 |
| Self-hosted runner label | 1 / 24 |
| Unpinned direct remote action uses | 9 / 77 |

Read through the measurement contract of Section 3, the result is primarily methodological. Every agent job referenced sensitive access, and a declared repository write appeared in a minority (7 of 24); yet no job met the strict three-indicator definition, because the input indicator marks "present" only when an agent step literally references event text (Section 3.2), and in 23 of 24 jobs that flow was left unknown rather than confirmed. The dangerous ingredients are thus common in this sample while the confirmed combination is, by construction, absent from static configuration — precisely the gap between visible configuration and effective authority that the contract is designed to preserve, now observed on real repositories. A prevalence claim would require the frozen, metadata-excluded, token-collected sample and the reviewer study of Section 6.1; this run is a pilot of that protocol, not a substitute for it. The harness and the identity-free aggregate summary are included with the artifact; per the project's data policy, raw per-repository observations are regenerated by re-running rather than committed.

## 6 Protocol for deployment and live agent studies

### 6.1 Deployment configuration study

The deployment study asks how often the three indicators coexist in the observed eligible jobs, and how their distributions vary by event, credential category, runner label, dependency-reference form, and engine markers. It uses the same scanner and summarizer exercised in Section 5.3, but replaces the clone-based fetch with the token-based collector, applies fork and archived exclusion, and freezes the catalog, implementation, protocol, and collection interval before the main run. Collect default-branch snapshots of public, non-fork, non-archived repositories and retain every exclusion, timeout, cap, and truncated tree. The resulting frame is an index-derived nonprobability sample, not an exhaustive GitHub census.

Report repository, workflow, and job counts separately, followed by indicator counts and unknowns. The denominator for job co-occurrence is all eligible observed agent jobs, with unresolved fields reported alongside the candidate count. A repository summary instead counts repositories containing at least one candidate. Secret categories overlap. No binomial population-prevalence interval should be attached to this discovery design; resampling repositories can describe sample variability only under explicitly stated assumptions, without repairing selection bias.

Unity, Unreal, and Godot markers identify repository contents, not a commercial studio, team size, or the purpose of the agent job. A tree with missing markers and incomplete enumeration has unknown engine status. Multiple engines can be present. Game-related results should therefore be reported as descriptive marker subsets, with small-cell disclosure review, rather than claims about industry adoption or security staffing.

Validate a prespecified sample with two reviewers working independently from blank forms and frozen evidence. Report agreement before adjudication, disagreement reasons, and uncertainty in the labels. Agreement among detected jobs does not estimate recall: missed invocations require a separately selected unmatched-workflow sample. Kappa must remain undefined where its marginal distribution makes it undefined. No independent reviewer study or deployment-prevalence result is reported here.

### 6.2 Paired runtime study

The runtime study asks whether a fully implemented profile changes attacker success, legitimate task success, and resource use relative to a frozen baseline. Use only owned dedicated sandboxes and canary credentials. Freeze provider and model identifiers, action and agent revisions, policies, configuration hashes, attack sources, tasks, repetitions, and attacker-tuning budgets. Record platform defaults, including checkout and cache behavior, so a historical exploit is not mistaken for a current failure.

Use matched baseline and profile runs for each provider, model, task, attack, and repetition. Counterbalance execution order and reset state between independent runs. Include clean tasks as well as attacked tasks. Define separate oracles for canary disclosure, unauthorized mutation, persistence, availability, and task correctness, using trusted external observations rather than an agent's self-report. A baseline attack that cannot be reproduced under current conditions is an informative result, not evidence that the profile stopped it.

For completed attacked runs, report attacker-success counts with their denominator. Also report attempted runs and infrastructure or provider errors; errors have unknown attack outcomes and are not defenses. Among complete pairs where the baseline attack succeeds, report how many fail against the profile. This conditional comparison must accompany the full condition table because it selects baseline successes. Report clean and attacked task utility separately, with both raw task-success proportions and retention conditional on baseline task success.

Measure elapsed-time and token differences only for comparable observations, retaining missingness and excluding zero denominators from ratios. Repeated tasks and adaptive attacks can be dependent; any confidence interval must reflect the unit of replication and clustering. The artifact checks recorded evidence and computes summaries but supplies neither a live model adapter nor an independent oracle. No attack-prevention, task-utility, or runtime-overhead estimate is claimed until those experiments have been completed.

## 7 Discussion and threats to validity

The practical value of the framework is its separation of three claims that are easy to conflate: a configuration warrants review, an enforcement boundary restricts a capability, and an observed attack fails in a specific deployment. A team can act on the first without claiming the third. The narrow validator illustrates that architectural restrictions can be inspected deterministically, while its replay and semantic probes expose obligations that cannot be satisfied by schema checking alone. The illustrative run of Section 5.3 adds that the same separation holds on real repositories: common sensitive-access and write declarations did not, by themselves, yield a single confirmed three-indicator candidate.

The strongest confidentiality posture keeps sensitive values outside agent reach. Once an agent can read private source or an authorized tool can return secrets, even approved output channels can carry information. Similarly, a signed artifact can faithfully represent an unsafe build input. Credential separation, output authorization, software review, and provenance address related but distinct properties. A practical deployment must decide which content changes require human judgment and which bounded operations can safely proceed autonomously.

Construct validity is limited by textual patterns, heuristic credential categories, and the gap between declarations and runtime settings. Internal validity is limited by author-designed fixtures and a small validator that does not represent an entire agent runtime. The tests have not established whole-program soundness, recall, or exhaustive correctness. External validity is limited because no deployment sample, private studio workflow, independent label study, or live-agent trial is included; the Section 5.3 run is a small, non-random convenience sample collected through a substitute fetch path, without fork or archived exclusion, and cannot stand in for the deployment study. Current platform protections also make historical attack results version-specific. These limitations constrain the contribution to a method, architecture, and tested components.

## 8 Ethics and artifact availability

The reported exercises use constructed workflows, in-memory proposals, and read-only snapshots of public configuration. No third-party code is executed and no third-party repository is attacked. The illustrative run and the planned deployment study read public configuration without publishing a mapping of identifiable projects to suspected vulnerabilities; the released summary is aggregate and identity-free. Any later confirmed issue requires private disclosure under an agreed process; the present paper does not claim that maintainers were notified or that a disclosure study occurred. No proprietary employer source code, systems, or operational measurements are used.

The implementation is version 0.1.0. The manuscript's source inventory identifies 41 tracked files and their SHA-256 hashes; the matching snapshot is commit 87d25f22a428c65dbebe6aa2ecc9b3eb3f323904 in the public repository seanudeke/agents.keys. The materials include the component reproduction script, observations, regression log, source inventory, and the illustrative-run harness and aggregate summary. The implementation has not undergone independent artifact evaluation or peer review.

## 9 Conclusion

Agents With Keys connects observable CI configuration to explicit enforcement obligations and an experiment protocol that preserves the distinction between evidence and authority. The prototype passes its offline regression suite, demonstrates both closed-schema restrictions and residual replay and semantic limits, and runs end to end over public repositories as an illustrative exercise. The deployment and live-agent studies remain separate empirical work. This foundation makes the next research step precise: implement and verify the complete boundaries, collect a documented sample, and measure real outcomes without promoting unknown settings or component checks into security guarantees.

## Acknowledgments

OpenAI ChatGPT through Codex assisted with literature discovery, drafting and revision across all sections, and preparation of the figure and reproduction materials. Anthropic's Claude assisted with reference verification, the illustrative public-repository run of Section 5.3, and this revision. Bibliographic metadata and technical claims were checked against the primary sources cited below. This disclosure follows IEEE guidance for generated content [17].

## References

[1] S. Wang, X. Hou, Z. Liu, Y. Zhao, X. Cheng, Q. Zou, X. Zhang, and H. Wang, "Demystifying and Detecting Agentic Workflow Injection Vulnerabilities in GitHub Actions," arXiv:2605.07135v1, 2026. doi: 10.48550/arXiv.2605.07135. https://arxiv.org/abs/2605.07135v1

[2] J. Isbarov, U. Suleymanov, I. Shumailov, and M. Kantarcioglu, "GitInject: Real-World Prompt Injection Attacks in AI-Powered CI/CD Pipelines," arXiv:2606.09935v1, 2026. doi: 10.48550/arXiv.2606.09935. https://arxiv.org/abs/2606.09935v1

[3] Meta, "Agents Rule of Two: A Practical Approach to AI Agent Security," Oct. 31, 2025. Accessed Oct. 18, 2026. https://ai.meta.com/blog/practical-ai-agent-security/

[4] GitHub, "Workflow syntax for GitHub Actions," documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

[5] GitHub, "OpenID Connect reference," documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/reference/security/oidc

[6] I. Koishybayev, A. Nahapetyan, R. Zachariah, S. Muralee, B. Reaves, A. Kapravelos, and A. Machiry, "Characterizing the Security of Github CI Workflows," in Proc. 31st USENIX Security Symposium, 2022, pp. 2747-2763. https://www.usenix.org/conference/usenixsecurity22/presentation/koishybayev

[7] SLSA, "Build: Requirements for producing artifacts," SLSA Specification v1.2. Accessed Oct. 19, 2026. https://slsa.dev/spec/v1.2/build-requirements

[8] E. Debenedetti et al., "Defeating Prompt Injections by Design," arXiv:2503.18813v2, 2025. doi: 10.48550/arXiv.2503.18813. https://arxiv.org/abs/2503.18813v2

[9] T. Shi, J. He, Z. Wang, H. Li, L. Wu, W. Guo, and D. Song, "Progent: Securing AI Agents with Privilege Control," arXiv:2504.11703v3, 2026. doi: 10.48550/arXiv.2504.11703. https://arxiv.org/abs/2504.11703v3

[10] GitHub, "Under the hood: Security architecture of GitHub Agentic Workflows," GitHub Blog, Mar. 9, 2026. Accessed Oct. 18, 2026. https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/

[11] GitHub, "GitHub Agentic Workflows," source repository and MIT license. Accessed Oct. 18, 2026. https://github.com/github/gh-aw

[12] GitHub, "Safer pull_request_target defaults for GitHub Actions checkout," June 18, 2026, updated July 15, 2026. Accessed Oct. 19, 2026. https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/

[13] GitHub, "Workflow dependency lockfiles," documentation, public preview. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles

[14] GitHub, "Secure use reference," documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/reference/security/secure-use

[15] GitHub, "Read-only Actions cache for untrusted triggers," June 26, 2026. Accessed Oct. 19, 2026. https://github.blog/changelog/2026-06-26-read-only-actions-cache-for-untrusted-triggers/

[16] GitHub, "REST API endpoints for search," documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28

[17] IEEE, "Submission Policies," IEEE Author Center Conferences, section Guidelines for Artificial Intelligence Generated Text. Accessed Oct. 18, 2026. https://conferences.ieeeauthorcenter.ieee.org/author-ethics/guidelines-and-policies/submission-policies/

---

### Reviewer-facing change log (v2, 2026-10-19) — delete before submission

- Added Section 5.3 and Table 3: an illustrative run of the scanner + summarizer over 9 public repositories / 24 agent jobs. Numbers produced by the unmodified `scanner` and `reporting.summarize`. It is a convenience sample via a substitute fetch path (grep.app discovery, anonymous clone), no fork/archived exclusion — stated as such; no prevalence or game claim.
- Abstract, Section 1 (third contribution), Section 6.1, Section 7, Section 8 updated to reference the run and keep its scope honest.
- Section 8: repository is now public; "working repository is private" and "review access must be arranged" removed accordingly.
- Acknowledgments: added Claude's role (reference verification, the Section 5.3 run, this revision), alongside the existing ChatGPT/Codex disclosure.
- References verified against primary sources this revision: [1] TaintAWI 2605.07135, [2] GitInject 2606.09935, [9] Progent 2504.11703 (current v3 title), [7] SLSA v1.2 build-requirements, [12] and [15] GitHub changelog posts. Still to click through before submission: [8] CaMeL, [10] GitHub agentic-workflows blog, [4][5][13][14][16] GitHub docs, [3] Meta, [6] Koishybayev, [11] gh-aw, [17] IEEE.
- Title: punctuation/hyphenation only. Consider, on your pass, a title that does not say "Measuring … Authority" (the paper measures configuration indicators, not authority or prevalence) — e.g., "Agents With Keys: A Measurement Contract and Least-Privilege Profile for AI Agents in CI."
