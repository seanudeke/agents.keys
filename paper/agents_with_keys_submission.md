# Agents With Keys: Measuring and Constraining Authority in AI-Enabled CI

Osita Sean Keluo-Udeke

## Abstract

AI coding agents combine contributor-controlled text with CI credentials and state-changing tools. Assessing their authority requires separating visible configuration from effective runtime capability. We present Agents With Keys, an authority-evidence contract connecting three-valued configuration indicators, an eight-control least-privilege profile, and a reproducible evaluation protocol. The prototype implements bounded parsing, versioned agent discovery, immutable snapshots, aggregate reporting, a closed-schema proposal validator, and recorded-trial evidence checks. A bounded GitHub index collection selected 300 public, non-fork, non-archived repositories and yielded 462 recognized agent jobs in 267 repositories; seven snapshots failed and four were partial. Forty-eight observed jobs (10.4%) met all three configuration indicators, while input flow remained unknown in 395 jobs. These are review candidates, not confirmed vulnerabilities or a population-prevalence estimate. All 90 offline regression tests passed, and ten deterministic validator checks matched expectations. Separate probes show that accepted proposals remain replayable and allowed labels can be wrong for the task. The framework links audit observations to explicit enforcement obligations while preserving the limits of each kind of evidence. Independent classification review and a paired live-agent defense evaluation remain outstanding.

Keywords: agentic engineering, continuous integration, prompt injection, least privilege, software supply chain

## 1 Introduction

An automated issue-triage agent seems distant from a release-signing system. On a shared CI runner, however, the distance between them depends on credentials, filesystem access, network paths, and downstream jobs. An injected issue description need not defeat the model’s reasoning if the surrounding workflow already gives the agent a route to a sensitive effect. Conversely, an alarming YAML fragment does not establish that a usable credential or attacker-reachable execution path exists.

Prior research has established that this is a substantive attack surface. TaintAWI analyzes flows from GitHub event data into agent prompts and downstream sinks [1]. GitInject exercises attacks in live, isolated GitHub workflows and examines workflow-level countermeasures [2]. We build on this work by connecting what an audit observes, what an enforcement mechanism actually controls, and what an experiment can legitimately conclude.

Meta’s Agents Rule of Two identifies the combination of untrusted input, sensitive access, and state change or external communication as requiring particular caution. Where all three are necessary, its guidance calls for supervision or reliable validation [3]. Translating that guidance into CI is difficult because a GitHub job is not necessarily one isolated agent session, a read-only repository token does not eliminate network effects, and a second job can still execute an unsafe model-derived proposal.

This paper contributes three things. First, it defines an auditable measurement contract that preserves unknowns and distinguishes credential references from effective authority. Second, it specifies eight controls as enforcement obligations, including the assumptions needed for bounded effects. Third, it provides a tested prototype and a dated, metadata-screened collection of public workflow configurations, with explicit missingness, denominators, and reproducibility commitments. Independent label validation and live-agent defense evaluation remain separate work. The contribution is a research method and prototype; it is not a completed census, a replacement for taint analysis, or a demonstrated defense against published attacks.

## 2 Background and related work

### 2.1 CI authority and agent workflows

GitHub Actions executes workflow jobs with event-dependent tokens, optional secrets, and runner resources. Declared token permissions can be overridden at job scope; effective permissions also depend on repository settings and event policy [4]. OIDC permission permits requesting an identity token, but does not by itself authorize a cloud resource operation [5]. An agent can also acquire authority through application tokens, checkout credentials, subprocesses, mounted files, tool servers, or a later workflow that trusts its artifacts. The relevant object of analysis is therefore an authority path, not only a token declaration.

Koishybayev et al. examined CI admission, execution, code, and secret access before the present agent ecosystem [6]. Their historical findings motivate permission analysis, but cannot be reused as contemporary agent-deployment estimates. SLSA v1.2 specifies isolation and protection of provenance-signing material at its higher build level [7]. Those requirements concern build integrity; conforming provenance does not establish that an agent’s review or proposed patch is correct.

### 2.2 Injection analysis and enforcement

TaintAWI models prompt-to-agent and prompt-to-script injection and analyzes invocation guards, derived outputs, and security-sensitive sinks [1]. GitInject studies actual CI execution semantics, including configuration files, credential handling, and infrastructure boundaries [2]. Our scanner has a substantially narrower role: it records reviewable configuration indicators without attempting comparable interprocedural taint analysis or exploit confirmation.

CaMeL separates control and data flow and mediates capabilities [8]. Progent represents privileges as policies over tool calls and constrains policy expansion [9]. GitHub Agentic Workflows combines isolation, mediated credentials, constrained outputs, and logging [10]; its implementation is publicly available under an MIT license [11]. Our profile organizes enforcement and measurement requirements across existing workflows, while the prototype implements only selected components. Comparative security and performance evaluation against these systems remains future work.

Table 1. Scope of related systems and the present artifact. Static and runtime refer to the principal analysis or control layer; attack evidence is the cited work's evaluation, not a common benchmark.

| System | Static layer | Runtime layer | Taint or flow analysis | Enforcement | Attack evidence |
|---|---|---|---|---|---|
| TaintAWI [1] | Workflow analysis | Confirmation | Workflow taint | Detection focus | CI exploit confirmation |
| GitInject [2] | Workflow inspection | Live CI | Not its central method | Countermeasures evaluated | CI exploit confirmation |
| CaMeL [8] | Trusted plan extraction | Tool mediation | Control/data separation | Capabilities | Benchmark attacks |
| Progent [9] | Policy reasoning | Tool mediation | Not its central method | Tool policy | Benchmark attacks |
| gh-aw [10], [11] | Workflow compilation | Isolated execution | Not general CI taint | Mediated effects | No common comparison here |
| Agents With Keys scanner | Configuration indicators | None | No transitive taint | None | None |
| Agents With Keys profile / prototype | Audit contract | Proposed services | None | Schema component only | Deterministic checks only |

The distinctive contribution is an authority-evidence contract: a static observation, an enforcement obligation, and an experimental outcome have different meanings and require different evidence. Table 1 makes that scope explicit. The prototype complements workflow taint analysis and live attack testing; its current results do not establish stronger security or lower overhead than those systems.

## 3 Threat model and measurement contract

### 3.1 Attacker and trusted components

The attacker can contribute text or files through an issue, comment, pull request, or another input consumed by an agent. The attacker initially lacks valid target credentials and permission to change the trusted default-branch workflow. We consider unauthorized disclosure, repository or release mutation, persistent influence, and manipulation of legitimate task outcomes. The model may follow injected instructions; the security argument does not depend on reliable refusal.

The proposed enforcement design trusts the CI control plane, isolation substrate, credential service, effect service, and reviewed policy. An attacker may control the proposal these components receive. Compromise of a trusted component is outside the conditional argument, but remains relevant to deployment review. A job boundary counts as a security boundary only when shared state, credentials, and communication paths are separately constrained. Neither successful parsing nor a provider’s tool-setting label demonstrates that isolation.

### 3.2 Three static indicators

For each recognized agent job, the scanner records the fields in Table 2. These are operational definitions for the artifact, not direct measurements of the three runtime properties in the Rule of Two. The input indicator matches textual event-field patterns anywhere within an agent step, including conditions, environment fields, and ordinary strings. A match establishes neither expression evaluation nor a prompt flow. The sensitive-access indicator includes model-key references and declared OIDC minting opportunities. It does not establish that the referenced secret exists or is reachable by the agent process.

Table 2. Configuration indicators and their interpretation

| Field | Present | Absent or unknown |
| --- | --- | --- |
| Input indicator | Matched event-field text pattern in an agent step | Otherwise unknown; indirect input flow is unresolved |
| Sensitive indicator | Visible secret reference or declared OIDC minting opportunity | Otherwise unknown; runtime reachability is unresolved |
| Declared repository write | Explicit token write declaration other than OIDC | Absent for an explicit declaration without such writes; unknown for inherited or dynamic values |

A job with all three indicators present is a review candidate. It is not a confirmed vulnerability. A negative candidate flag is also not a clean bill of health: its input or credential field may be unknown, another credential may grant writes, or external communication may remain available. The scanner reports egress enforcement, actor-gate correctness, tool enforcement, and runner ephemerality as unresolved unless established separately. A self-hosted label alone is not evidence of persistence.

### 3.3 Separating declarations from capability

Consider three constructed issue-triage workflows. Each references the issue body in an agent step. With a model-key reference and issues: write, all three indicators are present. Changing the declaration to contents: read makes the repository-write indicator absent, but leaves egress unknown. Removing the visible key reference changes the sensitive indicator to unknown, not absent. These exact outputs are reproduced by the component study. The examples expose an interpretation hazard: removing a YAML expression can remove evidence without removing authority.

The unit of static reporting is one job in one workflow path at one repository snapshot. Multiple agent invocations within that job do not create independent jobs. Identical file contents at different paths remain different observations. Agent-family and engine-marker groups can overlap, so their counts are not a partition of the sample.

## 4 Least privilege as an enforcement contract

Figure 1 separates untrusted reasoning from trusted credential and effect mediation. The eight controls below describe a target architecture. They are not eight YAML switches, and the prototype does not implement the complete architecture.

![Authority boundaries](figure1.png)

Figure 1. Proposed execution and authority boundaries. The green validator is implemented; dashed service boxes are architectural requirements. The validator checks schema and target/run/revision binding and returns a non-authorizing receipt. Authorization, freshness, replay prevention, credential mediation, and effect execution are proposed responsibilities of the effect service. No live write path is implemented.

### 4.1 Credential and token boundaries

P1 Credential separation. Release, signing, store, cloud, and long-lived repository credentials must remain outside agent-reachable memory, environment variables, files, and tool responses. A model API key is also sensitive. Where remote inference is required, a separate gateway can hold the provider credential and enforce destination, request, and spending limits. The gateway, its logs, and any returned data become part of the trusted computing base. Merely omitting the key from a prompt is insufficient.

P2 Token minimization. Begin with no token permissions and grant the smallest explicit job-level set required for reading. Evaluate alternate application tokens, persistent checkout authentication, OIDC trust, and service credentials separately. A declaration such as contents: read constrains that token channel; it does not prohibit a subprocess from sending data over the network. OIDC should be authorized only where a separately reviewed task and cloud trust policy require it.

### 4.2 Effects and execution state

P3 Vetted effects. The agent emits an untrusted proposal, not an executable script. A trusted service validates a closed schema, allowed operation, target repository and object, originating run, immutable source revision, size limits, and task authorization. It must also enforce freshness, replay policy, and any required approval before using a narrowly scoped credential. It must not load code, policy, or executables from the proposal’s untrusted workspace. Moving a shell command into a later job merely relocates the injection sink.

P4 Fresh execution. Provision a fresh environment for each independent run and prevent influence through workspaces, processes, sockets, writable mounts, caches, and reusable artifacts. Record the actual lifecycle and cache producers rather than inferring them from runner labels. SLSA’s isolation requirements provide a relevant baseline [7], but do not establish the correctness of a particular agent deployment. Only explicitly accepted, provenance-bound outputs may cross into later trusted work.

### 4.3 Input, tools, dependencies and communication

P5 Input boundaries. Use trusted workflow and policy revisions. Keep contributor text and repository-supplied agent instruction files outside operator authority, including when the event was initiated by a maintainer. Validate who can trigger the job and which revision is checked out. GitHub’s June 2026 checkout changes refuse specified fork-head patterns in privileged contexts, with version-dependent coverage and opt-outs [12]. They do not establish that all remaining files or prompts are trustworthy.

P6 Tool mediation. Authorize typed operations and argument arrays at an enforcement point the agent cannot bypass. A shell allowlist is ineffective if another tool exposes an interpreter, equivalent filesystem access, or an unrestricted network client. Re-parsing a command can reveal structure but does not safely implement a complete shell policy. Where practical, replace general shell authority with specific read or transformation capabilities and verify that alternate paths are unavailable.

P7 Dependency immutability. Review dependency behavior and bind execution to approved revisions. GitHub’s workflow lockfiles, in public preview as of October 2026, record action commits and source repository identities, including specified transitive dependencies; reusable workflow dependencies have separate lockfile scope [13]. Where lockfiles are unavailable, direct full-commit pins and image digests remain useful controls [14]. Neither mechanism certifies benign behavior or freezes every dependency downloaded by action code. The prototype records direct pin syntax; it does not resolve lockfile or transitive execution semantics.

P8 Egress and audit. Enforce outbound policy outside the agent’s control, including tool servers and provider gateways. Approved destinations can still carry attacker-selected data, so destination filtering alone is not a confidentiality proof. Retain protected, redacted evidence of tool calls, authorization decisions, effects, and failures. Logs must not become a secondary secret-disclosure channel. GitHub’s June 2026 cache-token restrictions also affect specific cross-trust persistence paths and must be recorded when reproducing earlier attacks [15].

### 4.4 A conditional argument for bounded effects

**Scoping lemma.** Fix a trusted policy and run context outside agent control. If every route to a relevant mutation passes through a trusted effect service, and that service correctly enforces the policy on the operation, target, arguments, and current authorization state, then a mutation outside the permitted effect set cannot execute through that architecture. Any alleged first violation would require either an unmediated route or an incorrect authorization decision. This statement identifies the obligations a deployment must establish; it is not a novel security theorem or a verified property of the prototype.

The useful consequence is a separation between capability and task correctness. With the validator's fixed target and two permitted labels, every accepted proposal selects one of three nonempty, unordered label sets, regardless of the model's instructions. An injected instruction cannot add a third label or redirect the target through that schema, yet it can select the wrong permitted label. The component study exhibits exactly that failure. A bounded effect vocabulary therefore limits available operations without proving their semantic correctness, confidentiality, frequency, or suitability for a release decision. Complete mediation, authorization, freshness, and replay prevention remain separate implementation obligations.

## 5 Prototype and observed results

### 5.1 Implementation

The Python prototype has five connected functions: scan configuration, collect public snapshots, summarize indicators, validate bounded proposals, and validate recorded trial evidence. Its seed catalog contains five action references representing four families, including a legacy Qodo alias, plus five heuristic CLI rules. CLI rules can recognize additional jobs in collected repositories; action-based discovery does not cover the population of CLI-only deployments. Hosted review services without an observable workflow invocation are outside this frame.

Parsing is read-only and bounded to 1 MiB, 30,000 YAML events, 100 aliases, and a nesting limit. It preserves the on key, rejects unsafe tags, conflicting duplicate keys, recursive aliases, and unsupported document structures, and reports exclusions. It does not execute mined code, resolve arbitrary reusable workflows, expand every matrix, or analyze transitive shell behavior. Credential categories are name-based hypotheses. Both inherited authority and ambiguous references remain visible as uncertainty.

The collector records a catalog digest, query ledger, exact default-branch commit, source hashes, tree completeness, exclusions, and explicit request and repository budgets. Its read-only HTTP client bounds retries and prevents authenticated redirects to another destination. Search partitioning addresses the per-query return cap, not index coverage or a changing search population [16]. Per-run keyed repository identifiers reduce casual linkage; they do not make sensitive raw snapshots anonymous. Raw data and identity mappings require separate access control.

### 5.2 Completed validation

On October 19, 2026, all 90 offline regression tests passed in Python 3.12.14 with PyYAML 6.0.3. The six modules contain 29 scanner tests, 22 collection and reporting tests, 21 validator and trial-evidence tests, five HTTP-client tests, four CLI tests, and nine bounded-search, recorded-response, and partial-collection tests. Their fixtures cover malformed inputs, unknown permissions, capped collection, separate denominators, incomplete evidence, and errors that must not become successful defenses. These counts describe software checks, not independent samples of workflows or attacks.

The deterministic validator exercise contains ten cases. One proposal within the label policy and fixed context was accepted, while nine proposals involving target confusion, an unauthorized operation, an extra field, arbitrary label content, excess labels, or a Boolean issue number were rejected. Table 3 groups the exact observations. No model, live credential, repository mutation, or network attack was involved. Consequently, ten matching outcomes cannot be reported as a prompt-injection block rate.

Table 3. Deterministic output validator observations

| Constructed input group | Cases | Expected | Observed |
| --- | --- | --- | --- |
| Within-policy bounded label | 1 | Accept | 1 accepted |
| Repository issue run or revision mismatch | 4 | Reject | 4 rejected |
| Unauthorized operation or extra field | 2 | Reject | 2 rejected |
| Invalid label content or count | 2 | Reject | 2 rejected |
| Boolean issue identifier | 1 | Reject | 1 rejected |

Two additional probes delimit the result. Repeating the same valid proposal twice produced two accepted, identical receipts: the stateless validator does not implement replay protection. A proposal for documentation also passed when the constructed task oracle required needs-triage: schema acceptance did not establish task correctness. Exhausting the nonempty subsets of the two allowed labels produced three accepted label sets. This is a small, intentionally bounded capability, not a general patch or release authorization mechanism. The returned receipt explicitly does not authorize execution.

The recorded-trial validator rejects fixture records, missing or changed evidence, mismatched outcome files, duplicate paired conditions, and incompatible implementation revisions. Its hashes establish byte integrity relative to supplied records; an experimenter can still supply an invalid oracle or misleading log. The optional Docker command constrains a validator component, not an Internet-connected agent. Docker execution and the complete credential and effect services were not evaluated in this study.

### 5.3 Bounded deployment configuration study

A new collection on October 19, 2026 replaces the earlier convenience pilot as the paper's deployment evidence. The selection plan was fixed after query calibration and before analytic collection; it was not preregistered. For each of five action references, we retrieved the first 100 REST code-search results in default best-match order. Public hits yielded 410 distinct repository names. Sorting those names and applying the declared 300-repository budget excluded 110 from attempted collection. This design deliberately bounds cost and retains ranking, indexing, catalog, and lexical-selection biases [16].

Repository metadata confirmed that all 300 selected repositories were public, non-fork, and non-archived; no fork or archive exclusions arose in this selected frame. Each available default branch was resolved to a commit before workflow retrieval. Capture ran from 16:32 to 16:51 UTC. The connected GitHub read API supplied retained responses, which were replayed through the collector; replay was not a second sample. All 2,915 retrieved workflow blobs matched their Git object identifiers. During acquisition, error handling was corrected so a failed blob would not suppress other available workflows; the amendment was recorded before scanner analysis, without changing the catalog or scanner. Initial missing blob responses were completed before final analysis.

Seven repositories failed snapshot resolution. Of the remaining 293, 289 were fully analyzed and four were partial because 13 workflow files were rejected by the bounded parser. The other 2,902 workflow files were parsed. We observed 462 recognized agent jobs in 267 repositories, including ten jobs from partial snapshots. Failed snapshots and rejected workflows have unknown job counts; they are not counted as zero-agent configurations. Table 4 reports all available job observations, with the denominator stated for each measure.

Table 4. Observed deployment configuration, with incomplete cases retained in the collection ledger. Counts describe this index-derived sample only.

| Measure | Observation |
|---|---|
| Selected repositories | 300 of 410 discovered |
| Fully analyzed / partial / failed snapshots | 289 / 4 / 7 |
| Retrieved / parsed workflow files | 2,915 / 2,902 |
| Recognized jobs / repositories containing them | 462 / 267 |
| A: event-field pattern present / unknown | 67 / 395 jobs |
| B: sensitive reference present / unknown | 459 / 3 jobs |
| C: declared write present / absent / unknown | 341 / 114 / 7 jobs |
| Three-indicator candidates | 48 / 462 jobs (10.4%) |
| Repositories containing a candidate | 26 / 267 (9.7%) |
| Model / non-model secret references | 421 / 339 jobs |
| Self-hosted runner label | 2 / 462 jobs |
| Unpinned direct remote-action uses in agent jobs | 623 / 1,186 (52.5%) |

The complete-snapshot sensitivity subset contains 452 jobs in 263 repositories, including 46 candidate jobs (10.2%) in 25 repositories. Excluding partial snapshots changes the descriptive fraction little, but does not bound the contribution of seven failed snapshots or unknown invocations. Agent-family counts overlap: 134 jobs matched a Claude action, 124 Gemini, 69 Codex, 141 Qodo, and one a Codex CLI rule. No recognized agent job was associated with the configured Unity, Unreal, or Godot markers; this sample supports no game-industry conclusion.

The main observation is the gap between declared authority and observable input flow. Repository-write declarations occur in 341 jobs, but the input indicator remains unknown in 395. The 48 three-indicator candidates identify a review queue, not 48 exploitable deployments. Conversely, the other jobs cannot be classified as safe: input may arrive through repository files, an action's implementation, serialized event data, scripts, or a downstream job. No independent precision, recall, exploitability, or defense-rate estimate is reported. The earlier 24-job pilot is retained in revision history and is not pooled into these counts.

### 5.4 Worked proposal repair

Consider the issue-labeling composition studied by TaintAWI [1], where one job exports agent-selected labels and another applies them. Our example uses a constructed, target-bound sandbox instance; the published target is not re-executed. The scanner describes the workflow, while the validator checks the proposal that would cross the effect boundary.

The example is rejected: `release-approved` is outside the permitted label set. Changing that label to `needs-triage` yields an accepted receipt. The receipt does not authorize a write. The reproduction script records both outcomes.

```json
{
  "version": 1,
  "operation": "add_labels",
  "repository": "research-owner/sandbox",
  "issue": 1,
  "run_id": "fixture-run",
  "source_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "labels": ["release-approved"]
}
```

This repair establishes schema membership and value binding only. A deployment would still need trusted policy loading, current authorization, freshness, replay and rate controls, and a credential-holding effect service. The accepted `documentation` probe in Section V-B shows why task correctness requires a separate oracle.

## 6 Independent validation and runtime-study protocol

### 6.1 Deployment configuration study

The bounded collection in Section V-C implements the observational part of the deployment protocol. Further study should extend discovery beyond the seed catalog and best-match page limit, retain all exclusions and snapshot failures, and assess whether the descriptive patterns persist under alternative discovery frames. Larger sample size alone does not remove selection bias or establish vulnerability prevalence.

Independent validation remains outstanding. Two reviewers should label a prespecified sample from blank forms against frozen workflow evidence, report agreement before adjudication, and retain disagreement reasons and unknowns. The released sampler and codebook support that process but do not supply independent judgments. Agreement within detected jobs does not estimate recall; missed invocations require a separately selected sample of unmatched workflows. Kappa must remain undefined where degenerate marginal distributions make it undefined. Repository-cluster resampling, if used, describes sample variability under stated assumptions rather than repairing index selection bias.

### 6.2 Paired runtime study

The runtime study asks whether a fully implemented profile changes attacker success, legitimate task success, and resource use relative to a frozen baseline. Use only owned dedicated sandboxes and canary credentials. Freeze provider and model identifiers, action and agent revisions, policies, configuration hashes, attack sources, tasks, repetitions, and attacker-tuning budgets. Record platform defaults, including checkout and cache behavior, so a historical exploit is not mistaken for a current failure.

Use matched baseline and profile runs for each provider, model, task, attack, and repetition. Counterbalance execution order and reset state between independent runs. Include clean tasks as well as attacked tasks. Define separate oracles for canary disclosure, unauthorized mutation, persistence, availability, and task correctness, using trusted external observations rather than an agent’s self-report. A baseline attack that cannot be reproduced under current conditions is an informative result, not evidence that the profile stopped it.

For completed attacked runs, report attacker-success counts with their denominator. Also report attempted runs and infrastructure or provider errors; errors have unknown attack outcomes and are not defenses. Among complete pairs where the baseline attack succeeds, report how many fail against the profile. This conditional comparison must accompany the full condition table because it selects baseline successes. Report clean and attacked task utility separately, with both raw task-success proportions and retention conditional on baseline task success.

Measure elapsed-time and token differences only for comparable observations, retaining missingness and excluding zero denominators from ratios. Repeated tasks and adaptive attacks can be dependent; any confidence interval must reflect the unit of replication and clustering. The artifact checks recorded evidence and computes summaries but supplies neither a live model adapter nor an independent oracle. No attack-prevention, task-utility, or runtime-overhead estimate is claimed until those experiments have been completed.

## 7 Discussion and threats to validity

The framework separates three claims: a configuration warrants review, an enforcement boundary restricts a capability, and an attack fails in a particular execution. The observed 48 candidates support the first claim. The closed-schema checks support a narrow part of the second. Neither constitutes the third. The large unknown-input category also makes a zero-candidate result in a small pilot difficult to interpret; larger, documented collection improves the evidence base without changing what an indicator means.

Confidentiality requires more than keeping release credentials outside the agent. Private source or an authorized tool's response can carry sensitive information, and approved output channels can transmit it. Likewise, a signed artifact can faithfully describe an unsafe build input. Credential separation, output authorization, task review, and provenance address distinct properties. Release and patch decisions need authorization appropriate to their consequences, beyond syntactic validity.

Construct validity is limited by textual matches, credential-name heuristics, incomplete GitHub schema validation, and the difference between declarations and runtime settings. The scanner does not resolve transitive actions, arbitrary scripts, reusable workflows, matrix instances, serialized event objects, or cross-job authority paths. Its input indicator may match ordinary text or a condition rather than prompt data. Four partial and seven failed snapshots leave additional uncertainty. The complete-snapshot subset is a sensitivity description, not a correction for missing data.

External validity is limited by five seed action references, best-match ranking, default search-index coverage, the lexical repository budget, snapshot timing, and correlated jobs within repositories. Public repositories do not represent private organizations, CLI-only deployments, or hosted bots, and engine-marker absence does not establish industry membership. Internal validity is limited by author-designed fixtures and the absence of independent classification labels, recall measurement, live attacks, and an implemented full mediation service. Current checkout and cache protections further make historical attacks version-dependent. These limitations bound the contribution to a measurement contract, a descriptive configuration sample, and tested components.

## 8 Ethics and artifact availability

The study reads public configuration and evaluates constructed proposals. No third-party repository code was executed, and no third-party repository was attacked or modified. The released deployment evidence consists of aggregates and digest commitments rather than project-to-finding mappings. Raw workflow snapshots, identity mappings, search responses, and collection logs are retained separately for controlled artifact inspection. Repeating discovery later produces a new sample; exact recomputation requires the retained snapshot bundle. No maintainer notification or independent disclosure study is claimed. No proprietary employer code, systems, or operational measurements are used.

The artifact is version 0.1.0 (tag `v0.1.0`) in the public repository https://github.com/seanudeke/agents.keys. It includes the source inventory, reproduction commands, component script and observations, regression log, collection plan and amendment, aggregate analysis, manuscript source, and figure source. `source_inventory.txt` hashes every other tracked regular file; it excludes itself to avoid a self-referential digest. The final inventory is committed before the manuscript's artifact commit is read. The artifact has not undergone independent artifact evaluation or peer review.

## 9 Conclusion

Agents With Keys connects observable CI configuration to explicit enforcement obligations and evidence requirements. The prototype's bounded collection yields 462 recognized agent jobs and 48 configuration review candidates while preserving missingness and unknown input paths. Deterministic checks demonstrate both a restricted proposal vocabulary and the remaining replay and semantic limitations. The next empirical steps are independent classification review and live evaluation of a fully implemented mediation boundary. The resulting claims can then be assessed against actual authority and outcomes rather than configuration hints alone.

## Acknowledgments

The author is responsible for the research design, interpretation, and final submission. OpenAI ChatGPT/Codex assisted with literature review, drafting and revision in Sections 1-9, Figure 1, and reproduction code. Anthropic Claude assisted with reference checking and an earlier pilot. Figure 1 was redrawn with Matplotlib to distinguish implemented components from proposed services. This disclosure follows IEEE policy [17].

## References

[1] S. Wang, X. Hou, Z. Liu, Y. Zhao, X. Cheng, Q. Zou, X. Zhang, and H. Wang, “Demystifying and Detecting Agentic Workflow Injection Vulnerabilities in GitHub Actions,” arXiv:2605.07135v1, 2026. doi: 10.48550/arXiv.2605.07135. https://arxiv.org/abs/2605.07135v1

[2] J. Isbarov, U. Suleymanov, I. Shumailov, and M. Kantarcioglu, “GitInject: Real-World Prompt Injection Attacks in AI-Powered CI/CD Pipelines,” arXiv:2606.09935v1, 2026. doi: 10.48550/arXiv.2606.09935. https://arxiv.org/abs/2606.09935v1

[3] Meta, “Agents Rule of Two: A Practical Approach to AI Agent Security,” Oct. 31, 2025. Accessed Oct. 18, 2026. https://ai.meta.com/blog/practical-ai-agent-security/

[4] GitHub, “Workflow syntax for GitHub Actions,” documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax

[5] GitHub, “OpenID Connect reference,” documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/reference/security/oidc

[6] I. Koishybayev, A. Nahapetyan, R. Zachariah, S. Muralee, B. Reaves, A. Kapravelos, and A. Machiry, “Characterizing the Security of Github CI Workflows,” in Proc. 31st USENIX Security Symposium, 2022, pp. 2747-2763. https://www.usenix.org/conference/usenixsecurity22/presentation/koishybayev

[7] SLSA, “Build: Requirements for producing artifacts,” SLSA Specification v1.2. Accessed Oct. 19, 2026. https://slsa.dev/spec/v1.2/build-requirements

[8] E. Debenedetti et al., “Defeating Prompt Injections by Design,” arXiv:2503.18813v2, 2025. doi: 10.48550/arXiv.2503.18813. https://arxiv.org/abs/2503.18813v2

[9] T. Shi, J. He, Z. Wang, H. Li, L. Wu, W. Guo, and D. Song, “Progent: Securing AI Agents with Privilege Control,” arXiv:2504.11703v3, 2026. doi: 10.48550/arXiv.2504.11703. https://arxiv.org/abs/2504.11703v3

[10] GitHub, “Under the hood: Security architecture of GitHub Agentic Workflows,” GitHub Blog, Mar. 9, 2026. Accessed Oct. 18, 2026. https://github.blog/ai-and-ml/generative-ai/under-the-hood-security-architecture-of-github-agentic-workflows/

[11] GitHub, “GitHub Agentic Workflows,” source repository and MIT license. Accessed Oct. 18, 2026. https://github.com/github/gh-aw

[12] GitHub, “Safer pull_request_target defaults for GitHub Actions checkout,” June 18, 2026, updated July 15, 2026. Accessed Oct. 19, 2026. https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/

[13] GitHub, “Workflow dependency lockfiles,” documentation, public preview. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/concepts/security/workflow-dependency-lockfiles

[14] GitHub, “Secure use reference,” documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/actions/reference/security/secure-use

[15] GitHub, “Read-only Actions cache for untrusted triggers,” June 26, 2026. Accessed Oct. 19, 2026. https://github.blog/changelog/2026-06-26-read-only-actions-cache-for-untrusted-triggers/

[16] GitHub, “REST API endpoints for search,” documentation. Accessed Oct. 18, 2026. https://docs.github.com/en/rest/search/search?apiVersion=2022-11-28

[17] IEEE, “Submission Policies,” IEEE Author Center Conferences, section Guidelines for Artificial Intelligence Generated Text. Accessed Oct. 18, 2026. https://conferences.ieeeauthorcenter.ieee.org/author-ethics/guidelines-and-policies/submission-policies/
