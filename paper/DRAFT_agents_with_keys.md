# Agents With Keys: How CI Pipelines Wire AI Coding Agents to Secrets and State, and a Least-Privilege Profile That Survives Published Attacks

**FIRST DRAFT — v0.1 (2026-10-17).** Target: AGENT 2027 (ICSE workshop), 8 pp incl. refs, IEEE template, single-anonymous, deadline Nov 13 2026.

> **READ BEFORE EDITING.**
> 1. **No results are invented.** Every place a number belongs is marked `⟦FILL FROM RUN⟧` or `⟦FILL FROM EXPERIMENT⟧`. The census (Sec. 5) needs the mining pipeline (`mine.py`) run on a real GitHub token; the defense evaluation (Sec. 7) needs the sandbox replays. Do not submit with any placeholder left.
> 2. **Citations need verification.** Keys below come from our research notes; several arXiv IDs were read via mirrors (alphaXiv, emergentmind) and must be checked against the real papers before submission. Do not cite anything you have not opened.
> 3. **AI-assisted drafting must be disclosed** in the acknowledgments per IEEE policy, naming the tool and the sections. You must be able to defend every sentence.
> 4. **Public data only.** No Zynga code, systems or metrics appear here. Keep it that way unless Legal clears specific material in writing.

---

## Abstract

AI coding agents — Claude Code, Gemini CLI, OpenAI Codex, Copilot, and LLM review bots — are now wired directly into continuous-integration (CI) pipelines, where they read issue text, pull-request titles and diffs and act through the same workflows that hold a project's build, signing, publishing and cloud credentials. A run of 2025–2026 disclosures (PromptPwnd, Comment-and-Control, GitInject, the Nx and Cline compromises) shows a single structural failure: an agent that ingests attacker-controlled text while holding a privileged CI token can be steered to exfiltrate secrets or tamper with releases, and string-based command guards do not stop it. We make three contributions. First, we define a **least-privilege configuration profile** for AI agents in CI, derived from the "Rule of Two" principle and expressed entirely in deployable GitHub Actions controls, that no model change is required to adopt. Second, we **measure how often real CI pipelines violate it**: across ⟦FILL FROM RUN: N⟧ public repositories that invoke an AI coding agent or LLM bot in CI, we find ⟦FILL FROM RUN: X%⟧ grant the agent job all three of untrusted input, credential access, and state-change power, and we break the exposure down by secret type, trigger, runner, and action-pinning, reporting the game-engine subset separately. Third, we **evaluate the profile** against ⟦FILL FROM EXPERIMENT: k⟧ published attack classes in a sandbox harness, showing it blocks ⟦FILL FROM EXPERIMENT⟧ while retaining ⟦FILL FROM EXPERIMENT⟧ of task utility. We release the scanner, the hardened reference workflows, and the profile as a checklist.

---

## 1. Introduction

Continuous-integration pipelines have become the highest-value target in the software supply chain: they run on every change, they hold the credentials that sign and publish releases, and a single poisoned run can reach every downstream user of a package. The 2020–2026 incident record — SolarWinds' build-time implant [CrowdStrike-SUNSPOT-2021], the Codecov uploader [Codecov-2021], the tj-actions and trivy-action tag compromises [CISA-tjactions-2025, Wiz-TeamPCP-2026], and the Nx and Cline package poisonings [Snyk-Nx-2025, Khan-Clinejection-2026] — reads as a steady migration of attacker attention from application code into the machinery that builds it.

Into that machinery teams are now placing AI coding agents. An agent action is given a task ("triage this issue," "review this PR," "fix this test"), a model key, and — in the default configurations teams copy from quick-start guides — the workflow's `GITHUB_TOKEN` and whatever build or publishing secrets the job already carried. The agent then reads text that people outside the project wrote: an issue body, a PR title, a review comment. That combination is exactly the one security engineers have learned to fear. Meta states it as the **Agents Rule of Two**: until prompt injection can be reliably refused, an agent session should hold at most two of (A) the ability to process untrusted input, (B) access to sensitive systems or secrets, and (C) the ability to change state or communicate externally [Meta-RuleOfTwo-2025]. A CI agent that reads an attacker's issue (A), holds a publishing token (B), and can push a commit or open a PR (C) holds all three.

The attacks that follow are no longer hypothetical. In 2026, independent researchers showed that the Claude Code, Gemini CLI, OpenAI Codex and Copilot agent actions all leak secrets when they process untrusted repository content while holding high-privilege tokens [Aikido-PromptPwnd-2025, CSA-CommentControl-2026]; a measurement paper confirmed hundreds of exploitable "agentic workflow injection" cases across thousands of public repositories [TaintAWI-2026]; and a reproducible framework, GitInject, found every tested provider vulnerable in its default configuration, for structural rather than model-specific reasons [GitInject-2026]. The Nx "s1ngularity" worm went further and weaponised the agents already installed on developer machines, driving Claude Code, Gemini and Amazon Q to inventory secrets [Snyk-Nx-2025].

Two things are still missing. The literature has mapped the *attacks* thoroughly but offers defenses that are either framework-level and not yet deployable in a stock pipeline (CaMeL's provable information-flow control [CaMeL-2026], Progent's policy DSL [Progent-2026]) or vendor-specific architectures teams cannot assemble from their own YAML [GitHub-AgenticWorkflows-2026]. And no one has measured how exposed real pipelines actually are — what fraction of deployed agent jobs violate the Rule of Two, which secrets sit in those jobs, and whether the teams least able to absorb a breach are the most exposed. Game studios are a sharp case of the second question: they are adopting hosted CI and AI tooling quickly, they hold unusually sensitive release credentials (store-publishing keys, platform SDK material, signing keys), and a 2025 interview study found their security work is reactive and under-resourced, especially at small studios [CISPA-GameSec-2025]. The Unity runtime vulnerability of October 2025 forced an industry-wide rebuild-and-reship of shipped titles [Unity-CVE-2025-59489], a reminder that a studio's build and release path is load-bearing for millions of players.

This paper addresses both gaps.

**Contributions.**
1. A **least-privilege configuration profile** for AI agents in CI (Sec. 6): eight controls, each a concrete GitHub Actions setting, that together guarantee no agent job holds all three Rule-of-Two properties. It is deployable today and requires no change to the underlying model.
2. An **exposure census** (Sec. 5) over ⟦FILL FROM RUN: N⟧ public repositories that run an AI coding agent or LLM bot in CI, quantifying how often each control is violated, broken down by secret category, trigger, runner type and action pinning, with the Unity/Unreal/Godot subset reported separately.
3. A **defense evaluation** (Sec. 7): a sandbox harness that replays ⟦FILL FROM EXPERIMENT: k⟧ published attack classes against default and profile-hardened pipelines, measuring block rate and the cost to task success and run time.

We release the scanner rules, the hardened reference workflows and the profile checklist so that practitioners can audit and fix their own pipelines.

---

## 2. Background and threat model

**GitHub Actions trust model.** A workflow is triggered by an event, runs one or more jobs on a runner, and is granted a `GITHUB_TOKEN` whose scopes the workflow declares under `permissions:`. Workflows may also read repository or organization *secrets* into the job environment. Some triggers carry content authored by people outside the project. `issues`, `issue_comment`, `pull_request_review_comment` and `discussion` events carry arbitrary text; `pull_request_target` runs in the context of the base repository — with its secrets — while checking out a fork's code, a combination long known to be dangerous. By contrast a plain `pull_request` from a fork runs without secrets. Third-party actions are referenced by `uses:` and run with the job's privileges; referencing them by mutable tag rather than commit SHA means a later force-push to that tag changes what runs, the mechanism behind the tj-actions and trivy-action compromises [CISA-tjactions-2025, Wiz-TeamPCP-2026].

**AI coding agents in CI.** An agent step is a `uses:` action (e.g., `anthropics/claude-code-action`, `google-github-actions/run-gemini-cli`, `openai/codex-action`) or a CLI invocation that sends a prompt, and often tool-use permissions, to a model and lets the model act — edit files, run shell commands, call the GitHub API, post comments, open PRs — through the surrounding job. LLM review bots (CodeRabbit, Qodo's pr-agent) are a narrower case: they read PR content and post comments. The Model Context Protocol (MCP) extends an agent's reach to external tools and servers; the GitHub MCP server, for example, exposes repository operations [Invariant-GitHubMCP-2025].

**Threat model.** We assume an attacker who can submit text that an agent in CI will read — open an issue, comment on a PR, set a PR title, file a discussion — but who has no write access to the target repository and no valid credentials. This is the standard "pwn request" / agentic-workflow-injection setting [TaintAWI-2026, GitInject-2026]. The attacker's goals are (i) exfiltrate secrets reachable from the agent job, (ii) tamper with build inputs or published artifacts, or (iii) persist on the runner. We treat the model as untrusted-by-default in the sense that we do not assume it will refuse injected instructions; the systematic review finds adaptive injection succeeds against state-of-the-art defenses more than 85% of the time [SoK-PromptInjection-2026]. Out of scope: attacks requiring valid write credentials, compromise of the model provider, and physical or supply-chain compromise of the runner image itself.

**The Rule of Two, applied to CI.** We adopt Meta's framing [Meta-RuleOfTwo-2025] as our organizing principle and specialize it to CI. For an agent *job* we define three properties: **A — untrusted input**, the job runs on an untrusted trigger or otherwise places event-authored text into the agent's prompt; **B — sensitive access**, the job's environment contains secrets beyond a model key, or runs on a persistent self-hosted runner, or holds `id-token`/`write-all`; **C — state change**, the job's token can alter repository state or publish (any write scope), or the agent can communicate outbound. A job holding all three is, by this rule, misconfigured regardless of which model it uses. The census measures how common that is; the profile removes at least one property from every agent job.

---

## 3. Related work

**CI/CD and GitHub Actions security.** A mature line of work measures misconfiguration in GitHub Actions. Koishybayev et al. found the overwhelming majority of workflows over-privileged [Koishybayev-USENIXSec-2022]; ARGUS and follow-on work characterized command-injection as pervasive [ARGUS-USENIXSec-2023]; Cosseter applies demand-driven static analysis to reduce permissions [Cosseter-SP-2026] and Granite enforces per-step permissions at runtime [Granite-2026]. Empirical studies cover reusable JavaScript actions [Delicheh-MSR-2024], the evolution of security practices over time [Huang-ICPC-2025], and a nine-scanner comparison that recommends an actionlint-plus-poutine baseline and finds zizmor the broadest single tool [Fares-Scanners-2026]. Our census reuses these methods but does not re-measure their axes; our unit of analysis is the *agent job* and its Rule-of-Two exposure, which this literature predates.

**Software signing, SBOM, provenance, reproducible builds.** Adjacent supply-chain work measures signing adoption [Schorlemmer-2024, Kalu-USENIXSec-2025], SBOM completeness [Xia-ICSE-2023, Bhuiyan-2026], and reproducibility at scale for Nix [Malka-MSR-2025] and F-Droid Android apps [Nanni-REP-2026]. SLSA's Build L3 requires run isolation and that signing-secret material be inaccessible to user-defined build steps [SLSA-v1.1]; cache poisoning has been shown to break L3 assumptions [Khan-CachePoisoning-2024]. These inform our profile's isolation controls but address artifact integrity rather than agent behavior. The field's research agenda is surveyed in [Williams-TOSEM-2025, Ladisa-SP-2023].

**Attacks on AI agents in pipelines.** This is the closest and most active area. TaintAWI/AWI formalizes agentic workflow injection and reports hundreds of confirmed-exploitable cases across thousands of repositories [TaintAWI-2026]; "Your AI, My Shell" measures prompt-injection success against coding editors [YourAIMyShell-2026]; GitInject runs real workflows in ephemeral repositories and finds every provider vulnerable by default [GitInject-2026]; MCPTox benchmarks tool-poisoning against live MCP servers [MCPTox-2026]; and a systematic review aggregates 78 studies [SoK-PromptInjection-2026]. Industry disclosures — PromptPwnd [Aikido-PromptPwnd-2025], Comment-and-Control with its associated CVEs [CSA-CommentControl-2026], and the Invariant GitHub-MCP toxic-flow [Invariant-GitHubMCP-2025] — document the same failure in shipping products. **Our contribution is deliberately not another attack demonstration.** We take these attacks as given and ask two different questions: how exposed is the deployed population, and does a configuration-level defense stop these published attacks at acceptable cost.

**Defenses.** CaMeL defeats prompt injection by design through information-flow control, solving 77% of AgentDojo tasks with provable security against 84% undefended, at a token-cost multiple [CaMeL-2026]; Progent reduces attack success to near zero with a tool-call policy DSL [Progent-2026]. Both operate at the agent-framework level and require adopting their runtime. GitHub's Agentic Workflows architecture gives agents no secrets, runs them in a firewalled container, and vets every write through a deterministic "safe outputs" channel [GitHub-AgenticWorkflows-2026] — the closest design to ours, but a proprietary platform rather than a profile a team can apply to an existing pipeline. OWASP's Top 10 for Agentic Applications [OWASP-Agentic-2025] catalogs risks without prescribing CI controls. Our profile translates the defensive principles these share into stock GitHub Actions configuration, so a team can adopt it incrementally without changing model, framework or platform.

**Game-development CI.** There is, to our knowledge, no prior empirical study of CI security in game-engine repositories. The nearest work is a thesis on Unity CI/CD *barriers* with no security focus [Aksli-2022] and a game-development security interview study that explicitly excludes CI and build security [CISPA-GameSec-2025]. This absence, together with games' distinctive release credentials, is why we report the game subset separately rather than as the whole population.

---

## 4. Methodology

Our census pipeline has five stages; all operate on public data through the GitHub REST API, and nothing found in a mined repository is ever executed.

**(1) Identify agent pipelines.** We search public `.github/workflows` files for each agent and LLM-bot action and CLI in a catalog we maintain (Table 1 ⟦FILL FROM RUN: finalize catalog counts⟧), covering autonomous coding agents (Claude Code, Gemini CLI, Codex, Copilot setup, Cursor, Aider, OpenCode) and LLM review bots (CodeRabbit, Qodo pr-agent, and ChatGPT-review variants). Because code search caps results per query, we partition large result sets by file size to enumerate exhaustively.

**(2) Repository metadata and filtering.** For each repository we record stars, fork and archived status, default branch and topics, and exclude forks and archived repositories from the denominator.

**(3) Engine detection.** We classify a repository as a game-engine project by markers in its file tree: `ProjectSettings/ProjectVersion.txt` (Unity), a `.uproject` file (Unreal), or `project.godot` (Godot). We report Unreal as a likely undercount, since much Unreal CI is self-hosted and not expressed in hosted-action YAML.

**(4) Workflow analysis.** For each agent workflow we parse the YAML and, for every job containing an agent step, extract: the triggers (classified as untrusted, conditional, or trusted); whether actor gating is present; the `permissions` mode and write scopes; referenced secrets, classified as model keys versus build/signing/store/cloud/repository credentials; self-hosted-runner use; third-party action count and how many are unpinned (not a 40-hex SHA); and whether a tool allowlist is declared. From these we compute the Rule-of-Two properties A, B and C per job. The analyzer is deterministic and unit-tested; it performs no network calls against the analyzed project and does not run its code.

**(5) Aggregation.** We report prevalence over the eligible population and, separately, over the game-engine subset, with confidence intervals ⟦FILL FROM RUN⟧.

**Reproducibility.** We release the catalog, scanner and (hashed, non-identifying) aggregate dataset. We do not release a list mapping individual repositories to exploitable configurations; see Sec. 10.

---

## 5. RQ1–RQ2: How exposed are real agent pipelines?

> **⟦THIS SECTION IS A SCAFFOLD. All numbers below are placeholders to be filled from the `mine.py` run on a real token. Do not submit with any ⟦…⟧ remaining.⟧**

**Population.** The search returned agent/LLM workflows in ⟦FILL FROM RUN: M⟧ public repositories; after removing forks and archived repositories, ⟦FILL FROM RUN: N⟧ remain, of which ⟦FILL FROM RUN: G⟧ are game-engine projects (Unity ⟦⟧, Unreal ⟦⟧, Godot ⟦⟧). First-pass tool-adoption floors from a public code-search index (grep.app, which indexes a subset of GitHub and counts files, so these are lower bounds), to be superseded by the exhaustive count:

| Agent / bot | Workflow files (floor) |
|---|---|
| `anthropics/claude-code-action` | 4,091 |
| `coderabbitai` (AI PR reviewer) | 1,200 |
| `pr-agent` (Qodo) | 810 |
| `google-github-actions/run-gemini-cli` | 252 |
| `openai/codex-action` | 248 |

*Table 1 (interim). Agent/LLM-bot adoption in public CI, floor counts. Replace with exhaustive per-repository counts from the run.*

**RQ1 — Rule-of-Two exposure.** Of ⟦N⟧ agent jobs, ⟦X%⟧ satisfy all three properties (A untrusted input, B sensitive access, C state change) and are thus misconfigured by the rule. ⟦breakdown: A∧B∧C vs each pair; share on untrusted triggers; share with no `permissions:` block (default-token exposure); share with visible actor gating⟧.

*Table 2. ⟦Rule-of-Two exposure, full population vs game subset.⟧*

**RQ2 — Secrets in the blast radius.** Among agent jobs that hold non-model secrets (⟦Y%⟧), the categories present are ⟦build / Android signing / Apple signing / store-publishing / cloud / registry-or-repo tokens⟧, with ⟦Z%⟧ holding at least one release-publishing credential. Game-engine jobs differ: ⟦e.g., UNITY_LICENSE prevalence, store keys⟧. Pinning and runners: ⟦% unpinned third-party actions; % on self-hosted runners⟧.

**Finding (to confirm).** We expect, consistent with [Koishybayev-USENIXSec-2022, TaintAWI-2026], that a substantial minority of agent jobs hold all three properties, and that release-publishing credentials are present in a non-trivial share. Whether the game subset is more or less exposed than the general population is the open empirical question this section answers — state the measured direction here, not an assumption. ⟦FILL FROM RUN⟧

---

## 6. A least-privilege profile for AI agents in CI

The profile removes at least one Rule-of-Two property from every agent job, using only stock GitHub Actions configuration. Each control cites the attack class it closes.

- **P1 — No secrets in the agent's context (removes B).** The agent job receives a model key only, ideally via an API proxy, and never the build, signing, store, cloud or long-lived repository tokens. Closes the credential-exfiltration path shown in [Aikido-PromptPwnd-2025, GitInject-2026].
- **P2 — Read-only default token (weakens C).** Set `permissions: contents: read` at workflow scope and grant nothing by default; the agent job gets no write scope.
- **P3 — Stage-and-vet all writes (breaks A∧C).** The agent cannot push, comment or open PRs directly. It emits structured proposed outputs that a *separate, non-agent* job — which holds write scope but ingests no untrusted text — validates, caps and applies. This is the "safe outputs" pattern generalized from [GitHub-AgenticWorkflows-2026] into project-level YAML.
- **P4 — Fresh, isolated runner per job; no shared cache across trust boundaries (removes persistence, supports B-isolation).** Use ephemeral hosted runners or ephemeral self-hosted runners that are destroyed after the run; never restore a cache written by a less-trusted context. Closes cache poisoning [Khan-CachePoisoning-2024] and persistent-runner abuse [PyTorch-runner-2024, Sha1Hulud-2025], and aligns with SLSA L3 run isolation [SLSA-v1.1].
- **P5 — Trigger hygiene (removes A where possible).** Do not run privileged agent steps on `issue_comment`, `issues`, `pull_request_target` or `discussion`. If the agent must read untrusted text, run it in the unprivileged `pull_request` context with no secrets. Treat all event-derived text as data, never instructions.
- **P6 — Tool allowlisting with re-parsing validation (reduces C surface).** Restrict the agent's tools, and validate commands/paths by re-parsing them, not by string matching, which the shell re-expands — the bypass class behind GuardFall and the quoted-text-stripping validator in [CSA-CommentControl-2026].
- **P7 — Pin third-party actions by commit SHA.** Closes tag force-push compromises [CISA-tjactions-2025, Wiz-TeamPCP-2026].
- **P8 — Constrain egress and log everything.** Restrict outbound network from the agent job and retain full logs, countering exfil-to-public-repo and enabling detection.

We provide hardened reference workflows implementing P1–P8 for the common agent actions, and a one-page checklist mapping each control to the Rule-of-Two property it removes.

**Relation to prior defenses.** CaMeL [CaMeL-2026] and Progent [Progent-2026] enforce injection resistance *inside* the agent framework with strong guarantees; our profile makes weaker per-task guarantees but is deployable on an existing pipeline today and composes with them. GitHub's platform [GitHub-AgenticWorkflows-2026] realizes a superset of P1/P3/P4 for users of that platform; the profile brings the same principles to teams on stock runners.

---

## 7. RQ3: Does the profile survive published attacks?

> **⟦THIS SECTION IS A SCAFFOLD. The attack battery is specified; the results are to be filled from sandbox replays. Invent nothing.⟧**

**Harness.** Following GitInject's ephemeral-repository method [GitInject-2026], we create sandbox repositories we control, deploy a baseline agent pipeline (typical quick-start configuration) and the P1–P8 profile pipeline, and replay a battery of published attack classes. All attacks run only against our own repositories. We test ⟦FILL: which agent actions / models⟧.

**Attack battery (specified; confirm exact set and provenance before running).** Prompt-to-Agent and Prompt-to-Script injection [TaintAWI-2026]; the GitInject families — config-file injection, credential exfiltration, judgment manipulation, availability [GitInject-2026]; comment/title/HTML-comment injection [CSA-CommentControl-2026]; cache poisoning [Khan-CachePoisoning-2024]; command-guard string-vs-shell bypass. Total ⟦k⟧ cases.

**Metrics.** Block rate per attack class (baseline vs profile); task utility retained (agent still completes its legitimate task) measured on ⟦FILL: a small suite of realistic triage/review/fix tasks, including game-build tasks⟧; and run-time/token overhead.

*Table 3. ⟦Block rate and utility, baseline vs profile, per attack class.⟧*

**Expected shape (to verify, not to assert).** The profile should block the credential-exfiltration and direct-write classes outright by construction (P1, P3), blunt persistence (P4) and tag-swap (P7) classes, and leave a residual where the agent's legitimate task itself requires a capability the attack also abuses — which is the honest limitation to report. Fill with measured block rates and the utility cost; if a class is not fully blocked, say so and explain why.

---

## 8. Discussion

**Why configuration, not model.** Injection resistance at the model layer is improving but unreliable [SoK-PromptInjection-2026]; the deployed exposure we measure in Sec. 5 exists now and is fixable now, without waiting for models to refuse injection. The profile is a floor, not a ceiling: teams that can adopt CaMeL/Progent or a managed agentic platform should.

**The under-resourced-studio angle.** If the census shows game-engine and small-team pipelines are at least as exposed as the general population while holding release-publishing credentials, the case for a copy-pasteable profile is strongest exactly where security staffing is thinnest [CISPA-GameSec-2025]. A studio forced into an emergency rebuild-and-reship, as Unity's 2025 vulnerability required industry-wide [Unity-CVE-2025-59489], does not want its agent pipeline to be the next incident.

**Deployability.** Every control is a setting teams already understand; P3 (stage-and-vet) is the only one that restructures a workflow, and we provide a reference implementation.

---

## 9. Limitations

- **Static analysis under-approximates.** We see configuration, not runtime; a job without visible gating may gate dynamically, and vice versa. We report what is statically evident and validate a sample manually ⟦FILL: sample size, agreement⟧.
- **Population bias.** Public repositories are not private enterprise pipelines; adoption floors from a partial index are lower bounds; Unreal CI is undercounted (Sec. 4).
- **No game build-pipeline-poisoning incident exists publicly.** Game-studio breaches to date are source/data theft and distribution-channel compromises, not agent-CI attacks [EA-2021, Riot-2023, Insomniac-2023]; our game motivation is prospective exposure, not a past game incident, and we say so.
- **The evaluation is not a proof.** It shows the profile blocks *these* published attacks; it is not a guarantee against future ones.
- **Attacks and tools move fast.** The named attack classes and CVEs are a 2025–2026 snapshot.

---

## 10. Ethics and responsible disclosure

All experiments run only against repositories we own; we never attack third-party projects. The census reads public configuration and executes nothing from mined repositories. We report exposure in aggregate and do **not** publish a mapping of individual repositories to exploitable configurations. Where the pipeline flags a plausibly exploitable public workflow, we notify the maintainer through a private channel and allow a disclosure window (target 45 days) before any identifying mention; the paper names no repository as exploitable without prior notification and consent. We disclose any new provider-level issues to the vendor before publication. The artifact we release (scanner, hardened workflows, checklist) is defensive and contains no working exploit payloads.

---

## 11. Conclusion

AI coding agents have been wired into CI pipelines faster than the pipelines have been re-secured for them, and the result is a population of jobs that read attacker-controlled text while holding the keys to a project's releases. We gave that exposure a precise definition via the Rule of Two, measured how widespread it is across public agent pipelines — reporting the game-engine subset separately — and showed that a least-privilege profile expressed entirely in stock CI configuration blocks the published attack classes at a modest cost to utility. The profile asks teams to change their YAML, not their model, which is why it can be adopted today by exactly the teams that can least afford the next supply-chain incident.

---

## Acknowledgments

⟦Disclose AI-assisted drafting here per IEEE policy: name the tool, version, and the sections it helped draft. Acknowledge the academic co-author, any maintainers who confirmed disclosures, and reviewers. Do not thank anyone who has not agreed to be named.⟧

## References

⟦Compile in IEEE format. Every key below must be verified against the actual source before submission; several arXiv IDs were read via mirrors and may be wrong. Do not cite anything unopened.⟧

- [Meta-RuleOfTwo-2025] Meta, "Agents Rule of Two: A Practical Approach to AI Agent Security," Oct 31 2025.
- [TaintAWI-2026] Wang et al., "Demystifying and Detecting Agentic Workflow Injection Vulnerabilities in GitHub Actions," arXiv 2605.07135 (verify ID).
- [GitInject-2026] Isbarov et al., "GitInject: Real-World Prompt Injection Attacks in AI-Powered CI/CD Pipelines," arXiv 2606.09935 (verify ID).
- [YourAIMyShell-2026] Liu et al., "'Your AI, My Shell': Demystifying Prompt Injection Attacks on Agentic AI Coding Editors," arXiv 2509.22040 / PACMSE (verify).
- [MCPTox-2026] Wang et al., "MCPTox: A Benchmark for Tool Poisoning Attack on Real-World MCP Servers," arXiv 2508.14925 (verify).
- [SoK-PromptInjection-2026] Maloyan & Namiot, systematic analysis of prompt-injection on agentic coding assistants, arXiv 2601.17548 (verify).
- [CaMeL-2026] Debenedetti et al., "Defeating Prompt Injections by Design (CaMeL)," arXiv 2503.18813.
- [Progent-2026] Shi et al., "Progent: Programmable Privilege Control for LLM Agents," arXiv 2504.11703.
- [GitHub-AgenticWorkflows-2026] GitHub, "Under the hood: Security architecture of GitHub Agentic Workflows," Mar 9 2026.
- [OWASP-Agentic-2025] OWASP, "Top 10 for Agentic Applications," Dec 9 2025.
- [Invariant-GitHubMCP-2025] Invariant Labs, "GitHub MCP exploited (toxic agent flow)," May 26 2025.
- [Aikido-PromptPwnd-2025] Aikido, "PromptPwnd: AI agents in GitHub Actions," via eSecurity Planet, Dec 4 2025.
- [CSA-CommentControl-2026] Cloud Security Alliance research note / Guan, Liu, Zhong, "Comment and Control," 2026 (CVE-2026-54316, CVE-2026-12537).
- [Koishybayev-USENIXSec-2022] Koishybayev et al., USENIX Security 2022.
- [ARGUS-USENIXSec-2023] ARGUS, USENIX Security 2023.
- [Cosseter-SP-2026] Tystahl et al., "Cosseter," IEEE S&P 2026.
- [Granite-2026] Moazen, Ahmadian, Balliu, "Granite," arXiv 2512.11602.
- [Delicheh-MSR-2024] Delicheh, Decan, Mens, MSR 2024.
- [Huang-ICPC-2025] Huang & Lin, ICPC 2025 ERA.
- [Fares-Scanners-2026] Fares, Gamage, Baudry, "Unpacking Security Scanners for GitHub Actions Workflows," arXiv 2601.14455 (verify).
- [Khan-CachePoisoning-2024] A. Khan, "The Monsters in Your Build Cache: GitHub Actions Cache Poisoning," May 6 2024.
- [SLSA-v1.1] SLSA v1.1 Build Track specification.
- [Williams-TOSEM-2025] Williams et al., "Research Directions in Software Supply Chain Security," ACM TOSEM 34(5), 2025.
- [Ladisa-SP-2023] Ladisa et al., "SoK: Taxonomy of Attacks on Open-Source Software Supply Chains," IEEE S&P 2023.
- [Schorlemmer-2024] Schorlemmer, Kalu et al., signing across four registries, arXiv 2401.14635.
- [Kalu-USENIXSec-2025] Kalu et al., industry interview study of software signing, USENIX Security 2025.
- [Xia-ICSE-2023] Xia et al., empirical study on SBOM, ICSE 2023.
- [Bhuiyan-2026] Bhuiyan et al., completeness/consistency of GitHub SBOMs, arXiv 2607.04614 (verify).
- [Malka-MSR-2025] Malka, Zacchiroli, Zimmermann, Nix reproducibility, MSR 2025.
- [Nanni-REP-2026] Nanni et al., F-Droid reproducibility, ACM REP 2026.
- [CrowdStrike-SUNSPOT-2021] CrowdStrike, "SUNSPOT: An Implant in the Build Process," 2021.
- [Codecov-2021] Codecov security update, 2021.
- [PyTorch-runner-2024] Stawinski/Khan (Praetorian), PyTorch self-hosted runner compromise, 2024.
- [CISA-tjactions-2025] CISA alert, tj-actions/changed-files (CVE-2025-30066), Mar 2025.
- [Snyk-Nx-2025] Snyk, Nx "s1ngularity" analysis, Aug 2025.
- [Sha1Hulud-2025] CISA / Datadog, Shai-Hulud npm worm, Sep/Nov 2025.
- [Khan-Clinejection-2026] A. Khan, "Clinejection," Feb 2026.
- [Wiz-TeamPCP-2026] Wiz / Phoenix Security, Trivy/TeamPCP supply-chain attack, Mar 2026.
- [Unity-CVE-2025-59489] Unity security advisory, CVE-2025-59489, Oct 2 2025.
- [CISPA-GameSec-2025] "Skipping the Security Side Quests: ... Security Practices and Challenges in Game Development," CISPA 2025.
- [Aksli-2022] Aksli, "Barriers and Solutions in CI/CD Implementation for Unity Game Development," BSc thesis, U. Tartu, 2022.
- [EA-2021], [Riot-2023], [Insomniac-2023] — game-studio breach reports (press), for the limitation in Sec. 9.
