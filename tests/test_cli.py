import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from awkeys.cli import main


class CliTests(unittest.TestCase):
    def test_local_scan_to_aggregate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root/"repo/.github/workflows"
            workflows.mkdir(parents=True)
            (workflows/"agent.yml").write_text("""
on: issues
permissions: {issues: write}
jobs:
  agent:
    runs-on: ubuntu-latest
    steps:
      - uses: openai/codex-action@v1
        with:
          prompt: ${{ github.event.issue.body }}
          key: ${{ secrets.OPENAI_API_KEY }}
""")
            out = root/"observations.jsonl"
            self.assertEqual(main(["scan", str(root/"repo"), "--output", str(out)]), 0)
            summary = root/"summary.json"
            self.assertEqual(main(["summarize", str(out), "--output", str(summary)]), 0)
            self.assertEqual(json.loads(summary.read_text())["all"]["agent_jobs"], 1)

    def test_parse_failure_visible_and_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workflows = root/"repo/.github/workflows"
            workflows.mkdir(parents=True)
            (workflows/"bad.yml").write_text("on: push\njobs: [")
            self.assertEqual(main(["scan", str(root/"repo"), "--output", str(root/"out.jsonl")]), 2)

    def test_boundary_cli_needs_no_tokens(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"boundary.json"
            self.assertEqual(main(["boundary-checks", "--output", str(path)]), 0)
            self.assertFalse(json.loads(path.read_text())["empirical_agent_evaluation"])

    def test_container_command_is_offline_and_pinned(self):
        script = Path(__file__).resolve().parents[1]/"scripts/run_boundary_container.py"
        spec = importlib.util.spec_from_file_location("container_runner", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        cmd = module.command("python@sha256:"+"a"*64, Path("/tmp/fixture-mount"))
        self.assertIn("--network=none", cmd)
        self.assertIn("--pull=never", cmd)
        self.assertIn("--read-only", cmd)
        self.assertIn("--cap-drop=ALL", cmd)
        self.assertNotIn("shell=True", str(cmd))
        with self.assertRaises(ValueError):
            module.command("python:latest", Path("/tmp/x"))


if __name__ == "__main__":
    unittest.main()
