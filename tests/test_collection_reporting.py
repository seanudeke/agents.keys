import base64
import json
import tempfile
import unittest
from pathlib import Path

from awkeys.github import BudgetExceeded, GitHubClient, GitHubError, search_partitioned
from awkeys.mining import collect, repository_id
from awkeys.reporting import reviewer_agreement, summarize, validation_sample, wilson
from awkeys.scanner import load_catalog, scan_workflow

WORKFLOW = """
on: issues
permissions: {contents: write}
jobs:
  a:
    runs-on: ubuntu-latest
    steps:
      - uses: openai/codex-action@v1
        with:
          prompt: ${{ github.event.issue.body }}
          openai-api-key: ${{ secrets.OPENAI_API_KEY }}
"""


class Fake:
    def __init__(self, response, max_requests=100):
        self.response = response
        self.requests, self.max_requests, self.audit = 0, max_requests, []
    def get(self, path, params=None):
        if self.requests >= self.max_requests:
            raise BudgetExceeded("test budget")
        self.requests += 1
        self.audit.append({"path": path})
        return self.response(path, params or {})


def item(name="o/r", path=".github/workflows/a.yml", sha="a", private=False):
    return {"repository": {"full_name": name, "private": private}, "path": path, "sha": sha}


class SearchTests(unittest.TestCase):
    def test_partition_when_result_cap_exceeded(self):
        def response(path, params):
            q = params["q"]
            if q.endswith("size:0..1"):
                return {"total_count": 1001, "items": []}
            return {"total_count": 1, "items": [item(path=q)]}
        hits, ledger = search_partitioned(Fake(response), "agent", low=0, high=1)
        self.assertEqual(len(hits), 2)
        self.assertTrue(all(x["returned_pages_complete"] for x in ledger))

    def test_indivisible_cap_is_recorded(self):
        fake = Fake(lambda p, q: {"total_count": 1001, "items": [item(path=str(i)) for i in range(100)]})
        _, ledger = search_partitioned(fake, "agent", low=1, high=1)
        self.assertTrue(ledger[0]["capped"])
        self.assertFalse(ledger[0]["returned_pages_complete"])

    def test_incomplete_search_is_recorded(self):
        _, ledger = search_partitioned(Fake(lambda p, q: {"total_count": 0, "items": [], "incomplete_results": True}), "a")
        self.assertFalse(ledger[0]["returned_pages_complete"])

    def test_private_results_are_discarded(self):
        hits, _ = search_partitioned(Fake(lambda p, q: {"total_count": 1, "items": [item(private=True)]}), "a")
        self.assertEqual(hits, [])

    def test_duplicate_search_hits_collapsed(self):
        hits, _ = search_partitioned(Fake(lambda p, q: {"total_count": 2, "items": [item(), item()]}), "a")
        self.assertEqual(len(hits), 1)

    def test_client_rejects_foreign_url(self):
        with self.assertRaises(GitHubError):
            GitHubClient("fixture-token").get("https://example.invalid")

    def test_client_requires_token_and_budget(self):
        with self.assertRaises(GitHubError):
            GitHubClient("")
        with self.assertRaises(ValueError):
            GitHubClient("fixture-token", max_requests=0)


class CollectionTests(unittest.TestCase):
    def response(self, path, params):
        if path.endswith("/commits/main"):
            return {"sha": "a"*40, "commit": {"tree": {"sha": "d"*40}}}
        if "/git/trees/" in path:
            return {"tree": [
                {"path": ".github/workflows/a.yml", "type": "blob", "sha": "b"*40},
                {"path": "ProjectSettings/ProjectVersion.txt", "type": "blob", "sha": "c"*40},
            ], "truncated": False}
        if "/git/blobs/" in path:
            return {"encoding": "base64", "content": base64.b64encode(WORKFLOW.encode()).decode()}
        return {"private": False, "fork": False, "archived": False, "default_branch": "main", "stargazers_count": 3}

    def test_explicit_snapshot_has_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"run"
            m = collect(Fake(self.response), output=root, catalog=load_catalog(), repositories=["o/r"])
            self.assertEqual(m["observation_count"], 1)
            self.assertTrue(m["snapshot_analysis_complete"])
            self.assertFalse(m["index_population_exhaustive"])
            r = json.loads((root/"observations.jsonl").read_text().strip())
            self.assertEqual(r["engines"], ["unity"])
            self.assertNotIn("o/r", r["repository_id"])
            self.assertEqual(len(list((root/"raw").rglob("*.yml"))), 1)

    def test_private_repository_not_collected(self):
        with tempfile.TemporaryDirectory() as directory:
            m = collect(Fake(lambda p, q: {"private": True}), output=Path(directory)/"run",
                        catalog=load_catalog(), repositories=["o/private"])
            self.assertEqual(m["observation_count"], 0)
            self.assertEqual(m["repositories"][0]["status"], "excluded")

    def test_request_budget_gives_partial_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/"run"
            m = collect(Fake(self.response, max_requests=1), output=root,
                        catalog=load_catalog(), repositories=["o/r"])
            self.assertFalse(m["snapshot_analysis_complete"])
            self.assertTrue((root/"manifest.private.json").is_file())

    def test_keyboard_interrupt_cannot_claim_complete_analysis(self):
        def interrupted(path, params):
            raise KeyboardInterrupt()
        with tempfile.TemporaryDirectory() as directory:
            m = collect(Fake(interrupted), output=Path(directory)/"run",
                        catalog=load_catalog(), repositories=["o/r"])
            self.assertFalse(m["snapshot_analysis_complete"])
            self.assertTrue(any(x["stage"] == "interrupted" for x in m["errors"]))

    def test_existing_run_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/"important").write_text("preserve")
            with self.assertRaises(ValueError):
                collect(Fake(self.response), output=root, catalog=load_catalog(), repositories=[])

    def test_repository_budget_visible(self):
        with tempfile.TemporaryDirectory() as directory:
            m = collect(Fake(self.response), output=Path(directory)/"run", catalog=load_catalog(),
                        repositories=["o/r", "o/s"], max_repositories=1)
            self.assertTrue(m["repository_budget_truncated"])
            self.assertFalse(m["snapshot_analysis_complete"])

    def test_hmac_salted_and_case_normalized(self):
        self.assertEqual(repository_id("O/R", b"a"), repository_id("o/r", b"a"))
        self.assertNotEqual(repository_id("o/r", b"a"), repository_id("o/r", b"b"))


class ReportingTests(unittest.TestCase):
    def rows(self):
        a = scan_workflow(WORKFLOW, repository_id="a", path="a.yml", engines=["unity"], engine_tree_complete=True)[0]
        b = scan_workflow(WORKFLOW, repository_id="b", path="b.yml")[0]
        c = {**a, "workflow_path": "c.yml", "triple_indicator_candidate": False}
        return [a, b, c]

    def test_job_and_repository_denominators(self):
        report = summarize(self.rows())
        self.assertEqual(report["all"]["triple_indicator_jobs"]["denominator"], 3)
        self.assertEqual(report["all"]["repositories_with_triple_indicator"]["denominator"], 2)
        self.assertEqual(report["engine_classification_unknown"]["agent_jobs"], 1)
        self.assertIsNone(report["population_prevalence_confidence_interval"])

    def test_duplicate_job_rejected(self):
        rows = self.rows()
        with self.assertRaises(ValueError):
            summarize(rows + [rows[0]])

    def test_empty_summary_has_no_false_zero_percent(self):
        self.assertIsNone(summarize([])["all"]["triple_indicator_jobs"]["percent"])

    def test_summary_contains_no_identifiers(self):
        report = json.dumps(summarize(self.rows()))
        self.assertNotIn("repository_id", report)
        self.assertNotIn("workflow_path", report)

    def test_validation_draw_is_reproducible_and_blind(self):
        a, b = validation_sample(self.rows(), 2, 8), validation_sample(self.rows(), 2, 8)
        self.assertEqual(a, b)
        self.assertEqual(a[0]["a_input_indicator"], "")

    def test_agreement_and_degenerate_kappa(self):
        sample = validation_sample(self.rows(), 2)
        for row in sample:
            for f in ("a_input_indicator", "b_sensitive_indicator", "c_declared_repository_write"):
                row[f] = "present"
        report = reviewer_agreement(sample, sample)
        self.assertEqual(report["a_input_indicator"]["observed_agreement"], 1)
        self.assertIsNone(report["a_input_indicator"]["cohens_kappa"])

    def test_agreement_rejects_unpaired_samples(self):
        with self.assertRaises(ValueError):
            reviewer_agreement(validation_sample(self.rows(), 1), [])

    def test_wilson_bounds_and_invalid_counts(self):
        self.assertEqual(wilson(0, 0), None)
        a, b = wilson(0, 10)
        self.assertGreaterEqual(a, 0)
        self.assertLess(b, 1)
        with self.assertRaises(ValueError):
            wilson(11, 10)


if __name__ == "__main__":
    unittest.main()
