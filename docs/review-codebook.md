# Independent review codebook

Review the frozen workflow and referenced evidence. Do not visit a project to execute its code or test an attack.

## Review fields

- a_input_indicator: present if an agent step references event-authored issue, discussion, review, comment, PR title/body, or commit text. Record in notes whether the reference is a prompt, environment, command, or condition. Unknown means the static view cannot establish the relevant path. This field is not a claim that the agent followed the text.
- b_sensitive_indicator: present for a visible secret reference, including a model key, or a declared id-token write scope. Unknown for unseen runtime reachability or inherited credentials. Record category ambiguity. A public YAML reference does not establish that the secret exists.
- c_declared_repository_write: present for an explicit repository-token write scope, absent for an explicit declaration with no repository write scopes, unknown for inherited or dynamic defaults. id-token is evaluated separately.

This task labels scanner indicators. A later exploitability review must additionally establish effective runtime credentials, network reachability, event authorization, transitive actions, and an attacker-controlled path. Do not merge those different tasks.

## Procedure

1. Freeze the snapshot and sample before labeling.
2. Each reviewer receives the same blank CSV and private snapshot lookup.
3. Reviewers record labels independently, without viewing scanner classifications or each other's labels.
4. Preserve the original files before calculating agreement.
5. Record adjudication reasons separately. Do not replace independent judgments with reconciled labels when reporting agreement.
6. Add a separately selected unmatched-workflow sample if estimating missed invocations or recall.

The CLI pairs reviews by repository identifier, workflow path, content hash, and job identifier. Identical contents in two workflow locations are distinct observations.

Actor checks, job conditions, fork approvals, and action pinning are evidence to interpret. Their presence is not proof of correct enforcement.
