import unittest

from awkeys.scanner import (
    WorkflowError, action_refs, agent_matches, engine_markers, load_catalog,
    load_workflow, permissions, scan_workflow, secret_refs,
)

WORKFLOW = """
on: issues
permissions:
  contents: write
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-code-action@v1
        with:
          prompt: ${{ github.event.issue.body }}
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
"""


def scan(text=WORKFLOW):
    return scan_workflow(text, repository_id="repo-a", path=".github/workflows/a.yml")


class ParsingTests(unittest.TestCase):
    def test_on_is_not_boolean(self):
        self.assertIn("on", load_workflow(WORKFLOW))

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(WorkflowError):
            load_workflow("on: push\non: issues\njobs: {}")

    def test_unsafe_tag_rejected(self):
        with self.assertRaises(WorkflowError):
            load_workflow("!!python/object/apply:os.system ['DO_NOT_EXECUTE']")

    def test_recursive_alias_rejected(self):
        with self.assertRaises(WorkflowError):
            load_workflow("on: push\njobs: &a {value: *a}")

    def test_alias_graph_finishes(self):
        text = "on: push\nx: &a [hello, hello]\ny: &b [*a,*a]\nz: &c [*b,*b]\njobs: {}"
        self.assertEqual(scan(text), [])

    def test_scalar_and_multidoc_rejected(self):
        for text in ("hello", "[]", "jobs: {}\n---\njobs: {}"):
            with self.subTest(text=text), self.assertRaises(WorkflowError):
                load_workflow(text)

    def test_oversize_rejected(self):
        with self.assertRaises(WorkflowError):
            load_workflow("a" * 1_048_577)

    def test_no_product_name_false_positive(self):
        catalog = load_catalog()
        for step in (
            {"name": "Claude Codex"}, {"run": "# claude -p hi\npip install claude"},
            {"run": 'echo "claude -p hi"'}, {"uses": "owner/claude-code-action@main"},
        ):
            self.assertEqual(agent_matches(step, catalog), [])

    def test_direct_cli_invocation(self):
        for run in ("claude -p 'review'", "codex exec 'review'", "gemini --prompt 'review'"):
            self.assertTrue(agent_matches({"run": run}, load_catalog()))

    def test_empty_non_agent_workflow(self):
        self.assertEqual(scan("on: push\njobs: {a: {steps: [{run: echo hello}]}}"), [])


class PermissionTests(unittest.TestCase):
    def test_inherited_unknown(self):
        self.assertEqual(permissions({}, {})["declared_write"], "unknown")

    def test_empty_means_none(self):
        self.assertEqual(permissions({"permissions": {}}, {})["declared_write"], "absent")

    def test_job_override_not_union(self):
        p = permissions({"permissions": "write-all"}, {"permissions": {"contents": "read"}})
        self.assertEqual(p["declared_write"], "absent")
        self.assertEqual(p["source"], "job")

    def test_oidc_is_separate_authority(self):
        p = permissions({"permissions": {"id-token": "write"}}, {})
        self.assertEqual(p["declared_write"], "absent")
        self.assertEqual(p["oidc"], "present")

    def test_write_all_and_read_all(self):
        self.assertEqual(permissions({"permissions": "write-all"}, {})["declared_write"], "present")
        self.assertEqual(permissions({"permissions": "read-all"}, {})["declared_write"], "absent")

    def test_dynamic_invalid_unknown(self):
        self.assertEqual(permissions({"permissions": "${{ inputs.perms }}"}, {})["declared_write"], "unknown")

    def test_invalid_oidc_read_is_not_treated_as_safe(self):
        self.assertEqual(permissions({"permissions": {"id-token": "read"}}, {})["declared_write"], "unknown")


class IndicatorTests(unittest.TestCase):
    def test_triple_is_configuration_candidate(self):
        row = scan()[0]
        self.assertTrue(row["triple_indicator_candidate"])
        self.assertEqual(row["record_kind"], "configuration_observation")
        self.assertEqual(row["egress_enforcement"], "unknown")

    def test_model_key_counts_as_sensitive(self):
        row = scan()[0]
        self.assertEqual(row["b_sensitive_indicator"], "present")
        self.assertTrue(row["model_secret_reference"])
        self.assertFalse(row["non_model_secret_reference"])

    def test_trigger_alone_does_not_prove_flow(self):
        row = scan(WORKFLOW.replace("${{ github.event.issue.body }}", "Review repository"))[0]
        self.assertTrue(row["untrusted_trigger_opportunity"])
        self.assertEqual(row["a_input_indicator"], "unknown")
        self.assertFalse(row["triple_indicator_candidate"])

    def test_prior_step_secret_included(self):
        text = WORKFLOW.replace("steps:\n", "steps:\n      - run: echo no-secret-values\n        env:\n          STORE: ${{ secrets.PLAY_STORE_KEY }}\n")
        self.assertTrue(scan(text)[0]["non_model_secret_reference"])

    def test_secret_brackets_and_dynamic(self):
        refs = secret_refs({"env": ["${{ secrets['AWS_KEY'] }}", "${{ secrets[matrix.name] }}"]})
        self.assertEqual(refs["names"], ["AWS_KEY"])
        self.assertTrue(refs["dynamic"])

    def test_raw_text_not_exported(self):
        row = scan(WORKFLOW.replace("prompt:", "prompt:"))[0]
        self.assertNotIn("github.event.issue.body", str(row))
        self.assertNotIn("anthropic_api_key:", str(row))

    def test_fork_runtime_uncertainty(self):
        row = scan(WORKFLOW.replace("on: issues", "on: pull_request"))[0]
        self.assertTrue(any("downgrade" in x for x in row["limitations"]))

    def test_visible_gating_is_not_validation(self):
        text = WORKFLOW.replace("runs-on:", "if: github.actor == 'maintainer'\n    runs-on:")
        row = scan(text)[0]
        self.assertTrue(row["visible_actor_condition"])
        self.assertFalse(row["actor_condition_validated"])

    def test_self_hosted_not_assumed_persistent(self):
        row = scan(WORKFLOW.replace("ubuntu-latest", "[self-hosted, linux]"))[0]
        self.assertEqual(row["runner"], "self_hosted_lifecycle_unknown")
        self.assertEqual(row["runner_ephemerality"], "unknown")

    def test_multiengine_markers(self):
        self.assertEqual(engine_markers(["x/ProjectSettings/ProjectVersion.txt", "y/game.uproject", "z/project.godot"]),
                         ["godot", "unity", "unreal"])

    def test_action_pin_kinds(self):
        refs = action_refs([{"uses": "a/b@" + "a"*40}, {"uses": "a/b@v1"},
                            {"uses": "./local"}, {"uses": "docker://x@sha256:"+"b"*64},
                            {"uses": "docker://x:latest"}])
        self.assertEqual([r["pinned"] for r in refs], [True, False, None, True, False])

    def test_catalog_has_no_setup_workflow_proxy(self):
        self.assertNotIn("copilot-setup-steps", str(load_catalog()["actions"]))


if __name__ == "__main__":
    unittest.main()
