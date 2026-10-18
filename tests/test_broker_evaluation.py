import copy
import json
import tempfile
import unittest
from pathlib import Path

from awkeys.broker import Context, Rejected, boundary_checks, validate_proposal
from awkeys.evaluation import TrialError, summarize_trials, validate_trials
from awkeys.io import sha256


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.context = Context("owner/sandbox", 1, "run", "a"*40)
        self.proposal = {"version": 1, "operation": "add_labels", "repository": "owner/sandbox",
                         "issue": 1, "run_id": "run", "source_sha": "a"*40, "labels": ["needs-triage"]}

    def test_closed_schema_accepts_authorized_operation(self):
        result = validate_proposal(json.dumps(self.proposal).encode(), self.context)
        self.assertFalse(result["execution_authorized_by_validator"])
        self.assertEqual(result["labels"], ["needs-triage"])

    def test_negative_boundary_cases(self):
        cases = [
            {"repository": "different/repo"}, {"issue": True}, {"issue": 2},
            {"run_id": "other"}, {"source_sha": "b"*40}, {"operation": "shell"},
            {"labels": []}, {"labels": ["unknown"]}, {"labels": ["needs-triage"]*2},
            {"command": "NO_EXECUTION"}, {"version": True},
        ]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(Rejected):
                validate_proposal(json.dumps({**self.proposal, **change}).encode(), self.context)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaises(Rejected):
            validate_proposal(b'{"version":1,"version":1}', self.context)

    def test_size_and_malformed_json(self):
        for payload in (b"x"*4097, b"[", b"\xff"):
            with self.assertRaises(Rejected):
                validate_proposal(payload, self.context)

    def test_boundary_results_explicitly_not_empirical(self):
        report = boundary_checks()
        self.assertFalse(report["empirical_agent_evaluation"])
        self.assertTrue(all(x["check_passed"] for x in report["checks"]))


class TrialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        data = {
            "protocol": "Frozen test-only protocol; not an executed study",
            "corpus": "Synthetic fixture tasks; never publication evidence",
            "baseline": "baseline fixture configuration",
            "profile": "profile fixture configuration",
            "log": "Fixture log; no agent was invoked",
            "baseline_oracle": json.dumps({"attacker_success": True, "task_success": True}),
            "profile_oracle": json.dumps({"attacker_success": False, "task_success": True}),
        }
        self.hashes = {}
        for name, value in data.items():
            (self.root/name).write_text(value)
            self.hashes[name] = sha256(value.encode())

    def tearDown(self):
        self.temp.cleanup()

    def trial(self, variant):
        # Explicitly test-only fabricated records for schema testing. Never shipped as study results.
        evidence = [{"path": name, "sha256": self.hashes[name], "role": role} for name, role in (
            ("protocol", "protocol"), ("corpus", "corpus"), (variant, "configuration"),
            ("log", "execution_log"), (variant+"_oracle", "outcome_oracle"))]
        return {"record_kind": "agent_trial", "trial_id": variant, "protocol_sha256": self.hashes["protocol"],
                "corpus_sha256": self.hashes["corpus"], "configuration_sha256": self.hashes[variant],
                "provider": "fixture-only", "model": "no-model", "agent_version": "test-only",
                "action_sha": "a"*40, "task_id": "task", "attack_id": "fixture",
                "repetition": 0, "variant": variant, "started_at": "2026-10-18T00:00:00+00:00",
                "status": "completed", "attacker_success": variant == "baseline", "task_success": True,
                "elapsed_seconds": 1.0, "input_tokens": None, "output_tokens": None, "evidence": evidence}

    def test_paired_reduction_denominator(self):
        report = summarize_trials([self.trial("baseline"), self.trial("profile")], self.root)
        self.assertEqual(report["complete_pairs"], 1)
        self.assertEqual(report["prevented_among_baseline_successful_attacks"]["denominator"], 1)
        self.assertEqual(report["prevented_among_baseline_successful_attacks"]["count"], 1)

    def test_fixture_record_cannot_enter_results(self):
        row = self.trial("baseline")
        row["record_kind"] = "deterministic_boundary_fixture_check"
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)

    def test_evidence_hash_mismatch(self):
        (self.root/"log").write_text("modified")
        with self.assertRaises(TrialError):
            validate_trials([self.trial("baseline")], self.root)

    def test_path_escape_and_symlink_rejected(self):
        row = self.trial("baseline")
        row["evidence"][0]["path"] = "../outside"
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)

    def test_outcome_must_match_oracle(self):
        row = self.trial("baseline")
        row["attacker_success"] = False
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)

    def test_error_is_not_a_blocked_attack(self):
        row = self.trial("profile")
        row.update(status="error", attacker_success=None, task_success=None)
        row["evidence"] = [x for x in row["evidence"] if x["role"] != "outcome_oracle"]
        result = summarize_trials([row], self.root)
        self.assertEqual(result["groups"][0]["errors"], 1)
        self.assertIsNone(result["groups"][0]["attack_not_successful"]["percent"])

    def test_error_cannot_claim_success(self):
        row = self.trial("profile")
        row["status"] = "error"
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)

    def test_duplicate_trials_rejected(self):
        row = self.trial("baseline")
        with self.assertRaises(TrialError):
            validate_trials([row, row], self.root)

    def test_nan_and_negative_time_rejected(self):
        for value in (float("nan"), -1, True):
            row = self.trial("baseline")
            row["elapsed_seconds"] = value
            with self.assertRaises(TrialError):
                validate_trials([row], self.root)

    def test_protocol_hash_must_match_evidence(self):
        row = self.trial("baseline")
        row["protocol_sha256"] = "c"*64
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)

    def test_paired_implementation_change_rejected(self):
        a, b = self.trial("baseline"), self.trial("profile")
        b["agent_version"] = "different"
        with self.assertRaises(TrialError):
            summarize_trials([a, b], self.root)

    def test_empty_evaluation_not_zero_attack_rate(self):
        result = summarize_trials([], self.root)
        self.assertIsNone(result["prevented_among_baseline_successful_attacks"]["percent"])

    def test_clean_tasks_are_not_counted_as_blocked_attacks(self):
        rows = [self.trial("baseline"), self.trial("profile")]
        for row in rows:
            row["attack_id"] = "clean"
            row["attacker_success"] = False
            row["evidence"] = [x for x in row["evidence"] if x["role"] != "outcome_oracle"]
            row["evidence"].append({"path": "profile_oracle", "sha256": self.hashes["profile_oracle"], "role": "outcome_oracle"})
        result = summarize_trials(rows, self.root)
        self.assertIsNone(result["groups"][0]["attack_not_successful"]["percent"])
        self.assertEqual(result["clean_utility_retained"]["count"], 1)
        self.assertEqual(result["paired_overhead"]["median_elapsed_ratio_profile_to_baseline"], 1)

    def test_missing_token_counts_are_not_zero_overhead(self):
        report = summarize_trials([self.trial("baseline"), self.trial("profile")], self.root)
        self.assertIsNone(report["paired_overhead"]["median_token_ratio_profile_to_baseline"])

    def test_invalid_action_revision_and_evidence_role(self):
        for change in ("action", "role"):
            row = self.trial("baseline")
            if change == "action":
                row["action_sha"] = None
            else:
                row["evidence"][0]["role"] = []
            with self.assertRaises(TrialError):
                validate_trials([row], self.root)

    def test_missing_oracle_and_boolean_token_counts_rejected(self):
        row = self.trial("baseline")
        row["input_tokens"] = True
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)
        row = self.trial("baseline")
        row["evidence"] = [x for x in row["evidence"] if x["role"] != "outcome_oracle"]
        with self.assertRaises(TrialError):
            validate_trials([row], self.root)


if __name__ == "__main__":
    unittest.main()
