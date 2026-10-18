# Inert examples

The workflow and proposal are teaching fixtures, not deployable hardened workflows or research observations.

Validate the closed-schema fixture:

    awkeys validate-proposal examples/proposal.json --repository research-owner/sandbox --issue 1 --run-id fixture-run --source-sha aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa --output runs/proposal-receipt.json

The receipt does not perform a write. Runtime authorization, replay control and an isolated credential/effect service remain required for a real deployment.

The exposure example intentionally contains a mutable action reference, event text and write permissions. It is stored outside the active workflows directory and is never executed by CI.
