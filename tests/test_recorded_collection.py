import json
import tempfile
import unittest
from pathlib import Path

from awkeys.cache import RecordedGitHubClient, request_key, response_digest
from awkeys.github import BudgetExceeded, GitHubError, search_bounded
from awkeys.mining import collect, search_queries
from awkeys.scanner import load_catalog
from test_collection_reporting import Fake, item
import test_collection_reporting as fixtures


class BoundedSearchTests(unittest.TestCase):
    def test_capped_best_match_page_is_not_complete(self):
        hits, ledger = search_bounded(Fake(lambda p, q: {
            "total_count": 2000, "items": [item(), item(), item(private=True)]}), "query")
        self.assertEqual(len(hits), 1)
        self.assertTrue(ledger[0]["capped"])
        self.assertFalse(ledger[0]["returned_pages_complete"])

    def test_complete_small_result_and_invalid_budget(self):
        _, ledger = search_bounded(Fake(lambda p, q: {"total_count": 1, "items": [item()]}), "query")
        self.assertTrue(ledger[0]["returned_pages_complete"])
        for budget in (0, 11, True):
            with self.assertRaises(ValueError):
                search_bounded(None, "query", max_pages=budget)

    def test_query_uses_rest_legacy_syntax(self):
        for query in search_queries(load_catalog()):
            self.assertIn("path:.github/workflows", query)
            self.assertNotIn("is:public", query)

    def test_snapshot_completeness_does_not_hide_capped_search(self):
        def response(path, params):
            if path == "/search/code":
                return {"total_count": 2000, "items": [item()]}
            return {"private": False, "fork": True, "archived": False}
        with tempfile.TemporaryDirectory() as directory:
            manifest = collect(Fake(response), output=Path(directory)/"run",
                               catalog=load_catalog(), search_pages_per_query=1)
        self.assertTrue(manifest["selected_snapshots_complete"])
        self.assertFalse(manifest["search_returned_pages_complete"])
        self.assertFalse(manifest["snapshot_analysis_complete"])
        self.assertEqual(manifest["repositories"][0]["status"], "excluded")


class RecordedResponseTests(unittest.TestCase):
    def record(self, root, path="/repos/o/r", params=None):
        response = {"private": False}
        entry = {"path": path, "params": params or {}, "response": response,
                 "response_sha256": response_digest(response),
                 "captured_at": "2026-10-19T00:00:00Z", "transport": "test_fixture"}
        target = root/(request_key(path, params)+".json")
        target.write_text(json.dumps(entry))
        return target, entry

    def test_replay_retains_capture_provenance_and_is_budgeted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.record(root)
            client = RecordedGitHubClient(root, max_requests=1)
            self.assertEqual(client.get("/repos/o/r"), {"private": False})
            self.assertEqual(client.audit[0]["at"], "2026-10-19T00:00:00Z")
            self.assertIn("replayed_at", client.audit[0])
            with self.assertRaises(BudgetExceeded):
                client.get("/repos/o/r")

    def test_tampering_is_not_silently_replayed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target, entry = self.record(root)
            entry["response"]["private"] = True
            target.write_text(json.dumps(entry))
            with self.assertRaises(GitHubError):
                RecordedGitHubClient(root).get("/repos/o/r")


    def test_missing_response_and_foreign_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            client = RecordedGitHubClient(Path(directory))
            for path in ("/missing", "https://example.invalid", "//example.invalid"):
                with self.assertRaises(GitHubError):
                    client.get(path)

    def test_request_identity_is_verified_separately_from_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target, entry = self.record(root)
            entry["params"] = {"different": 1}
            target.write_text(json.dumps(entry))
            with self.assertRaises(GitHubError):
                RecordedGitHubClient(root).get("/repos/o/r")


class PartialWorkflowTests(unittest.TestCase):
    def test_failed_blob_does_not_suppress_other_available_workflows(self):
        fixture = fixtures.CollectionTests()
        def response(path, params):
            if '/git/trees/' in path:
                return {'tree': [
                    {'path': '.github/workflows/a.yml', 'type': 'blob', 'sha': 'e'*40},
                    {'path': '.github/workflows/b.yml', 'type': 'blob', 'sha': 'b'*40},
                ], 'truncated': False}
            if path.endswith('/git/blobs/'+'e'*40):
                raise GitHubError('fixture fetch failure')
            return fixture.response(path, params)
        with tempfile.TemporaryDirectory() as directory:
            manifest = collect(Fake(response), output=Path(directory)/'run',
                               catalog=load_catalog(), repositories=['o/r'])
        self.assertEqual(manifest['observation_count'], 1)
        self.assertEqual(manifest['repositories'][0]['status'], 'partial')
        self.assertEqual(manifest['errors'][0]['stage'], 'workflow_fetch')
        self.assertFalse(manifest['selected_snapshots_complete'])



if __name__ == "__main__":
    unittest.main()
