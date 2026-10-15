"""Regression for decoded SDK tool arguments in completed observations."""
import copy
import json
import unittest

from harbor_patch.privileged_state.repair_state import completed_evidence


class ToolArgumentsTests(unittest.TestCase):
    def observe(self, arguments):
        messages = [
            {"role": "assistant", "tool_calls": [{"id": "x", "function": {
                "name": "terminal", "arguments": arguments}}]},
            {"role": "tool", "tool_call_id": "x", "content": json.dumps({
                "exit_code": 0, "output": "2 passed, 1 skipped"})},
        ]
        original = copy.deepcopy(messages)
        journal = {"seen": set(), "events": []}
        event = completed_evidence(messages, journal, "code-a")
        self.assertEqual(messages, original)
        repeated = completed_evidence(messages, journal, "code-b")
        self.assertEqual(len(journal["events"]), 1)
        self.assertEqual(repeated["freshness"], "stale")
        return event

    def test_decoded_and_json_arguments_have_same_evidence(self):
        arguments = {"command": "pytest tests/test_example.py", "timeout": 300}
        decoded = self.observe(arguments)
        self.assertEqual(decoded, self.observe(json.dumps(arguments)))
        self.assertEqual(decoded["test_report"], "2 passed, 1 skipped")
        self.assertEqual(decoded["test_freshness"], "unknown")

    def test_missing_or_non_test_arguments_do_not_infer_test(self):
        for arguments in (None, {}, "", {"command": "echo hello"}):
            with self.subTest(arguments=arguments):
                self.assertEqual(self.observe(arguments)["test_report"], "unknown")

    def test_unsupported_argument_type_still_fails_closed(self):
        with self.assertRaises(TypeError):
            self.observe(["pytest"])

    def test_pending_call_has_no_completed_evidence(self):
        journal = {"seen": set(), "events": []}
        messages = [{"role": "assistant", "tool_calls": [{"id": "x", "function": {
            "name": "terminal", "arguments": {"command": "pytest"}}}]}]
        self.assertEqual(completed_evidence(messages, journal, "code")["status"], "none")


if __name__ == "__main__":
    unittest.main()
