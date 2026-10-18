import io
import json
import unittest
from unittest.mock import MagicMock
from urllib.error import HTTPError
from urllib.request import Request

from awkeys.github import BudgetExceeded, GitHubClient, GitHubError, NoRedirect


class HttpClientTests(unittest.TestCase):
    def response(self, payload):
        response = MagicMock()
        response.read.return_value = json.dumps(payload).encode()
        response.status = 200
        response.headers = {"X-RateLimit-Remaining": "9"}
        context = MagicMock()
        context.__enter__.return_value = response
        return context

    def test_token_only_in_request_header_not_audit(self):
        client = GitHubClient("fixture-only-token", sleep=lambda n: None)
        client._opener.open = MagicMock(return_value=self.response({"total_count": 0}))
        result = client.get("/search/code", {"q": "fixture"})
        request = client._opener.open.call_args[0][0]
        self.assertEqual(request.get_header("Authorization"), "Bearer fixture-only-token")
        self.assertNotIn("fixture-only-token", json.dumps(client.audit))
        self.assertEqual(result["total_count"], 0)

    def test_auth_failure_is_sanitized_and_not_retried(self):
        client = GitHubClient("fixture-only-token", sleep=lambda n: None)
        client._opener.open = MagicMock(side_effect=HTTPError("https://api.github.com", 401,
            "fixture-only-token", {}, io.BytesIO(b"sensitive response")))
        with self.assertRaises(GitHubError) as caught:
            client.get("/repos/o/r")
        self.assertNotIn("fixture-only-token", str(caught.exception))
        self.assertEqual(client.requests, 1)

    def test_transient_failure_retries_with_budget(self):
        client = GitHubClient("fixture-only-token", sleep=lambda n: None)
        client._opener.open = MagicMock(side_effect=[
            HTTPError("https://api.github.com", 503, "temporary", {}, io.BytesIO()),
            self.response({"ok": True})])
        self.assertTrue(client.get("/repos/o/r")["ok"])
        self.assertEqual(client.requests, 2)

    def test_budget_is_a_hard_limit(self):
        client = GitHubClient("fixture-only-token", max_requests=1, sleep=lambda n: None)
        client._opener.open = MagicMock(return_value=self.response({}))
        client.get("/repos/o/r")
        with self.assertRaises(BudgetExceeded):
            client.get("/repos/o/s")
        self.assertEqual(client._opener.open.call_count, 1)

    def test_redirect_never_forwards_authorization(self):
        request = Request("https://api.github.com/repos/o/r", headers={"Authorization": "Bearer fixture-only-token"})
        self.assertIsNone(NoRedirect().redirect_request(request, None, 302, "redirect", {}, "https://example.invalid"))


if __name__ == "__main__":
    unittest.main()
