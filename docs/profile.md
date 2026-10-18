# Least-privilege profile and enforcement requirements

This is a design profile to evaluate. It is not a claim that eight YAML flags make an arbitrary agent secure.

| Control | Required mechanism | What static analysis can observe | What remains to validate |
| --- | --- | --- | --- |
| P1 Credential separation | Isolated model/API proxy and no release credentials in agent-reachable state | Secret references and categories | Actual credential reachability, proxy scope and quotas |
| P2 Token minimization | Explicit job permissions and removal of alternate credentials | Declared scopes and inheritance | Effective token scopes, app tokens, OIDC trust |
| P3 Vetted effects | Trusted validator, closed schema, target binding, bounded operations, authorization and replay protection | Separate stages and hints only | End-to-end authorization and output handling |
| P4 Fresh execution | Verified ephemeral substrate and cache trust separation | Runner labels, cache-action references | Lifecycle, filesystem isolation, cache producers and service policy |
| P5 Input boundaries | Restricted triggers, trusted base workflow, validated input flow | Events and event-text references | Gating logic, PR origin, transitive sources |
| P6 Tool mediation | Enforced capability boundaries and validated argument arrays | Tool-setting hints | Runtime enforcement, indirect tools, interpreters |
| P7 Dependency immutability | Reviewed commit/image pins and controlled update process | Direct action pin form | Transitive code, reviewed behavior, provenance |
| P8 Egress and audit | Enforced network boundaries and redacted, access-controlled audit | Configuration hints, not enforcement | Kernel/service behavior, covert channels, log disclosure |

The example validator permits only a small set of label values on one trusted issue context. It rejects extra fields, alternate repositories, other issues, other source revisions, and arbitrary content. It does not perform GitHub writes. Its receipt explicitly states that execution is not authorized by validation alone.

The validator does not implement replay protection, a credential proxy, an effect broker, or an agent sandbox. The offline container harness provides a bounded environment for its component tests, not an Internet-connected model runtime. These boundaries must be implemented and measured before claiming a full profile evaluation.

Setting contents: read does not remove external effects. A model API key is sensitive even when no release key is present. A downstream job still processes untrusted proposed output. Schema validity does not establish that an otherwise authorized code change is safe.
