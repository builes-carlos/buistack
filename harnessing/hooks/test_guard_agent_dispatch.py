#!/usr/bin/env python3
"""
Tests for guard_agent_dispatch.py.

No test convention exists in this repo yet (no unittest/pytest usage found anywhere
under harnessing/ or devaing/'s own scripts) -- this is a new, stdlib-only unittest
file, run directly:

  python harnessing/hooks/test_guard_agent_dispatch.py
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOK_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOK_DIR))

import guard_agent_dispatch as guard  # noqa: E402


def agent_input(session_id="sess-1", description="Faber: issue 98 distributors",
                 prompt="You are Faber, the builder.", model="sonnet", tool_name="Agent"):
    return json.dumps({
        "session_id": session_id,
        "tool_name": tool_name,
        "tool_input": {
            "description": description,
            "prompt": prompt,
            "model": model,
            "subagent_type": "general-purpose",
        },
    })


def run_hook(stdin_text: str, register_dir: Path) -> subprocess.CompletedProcess:
    """Run the hook as a real subprocess (the actual invocation contract), pointed
    at an isolated register directory via monkeypatched REGISTER_DIR -- done by
    running a tiny wrapper script rather than patching the user's real
    ~/.claude/harnessing directory.
    """
    wrapper = f"""
import sys
sys.path.insert(0, {str(HOOK_DIR)!r})
import guard_agent_dispatch as guard
from pathlib import Path
guard.REGISTER_DIR = Path({str(register_dir)!r})
sys.exit(guard.main())
"""
    return subprocess.run(
        [sys.executable, "-c", wrapper],
        input=stdin_text, capture_output=True, text=True,
    )


class TestRoleExtraction(unittest.TestCase):
    def test_description_prefix(self):
        self.assertEqual(guard.extract_role("Faber: build the thing", ""), "Faber")

    def test_case_insensitive_and_instance_suffix(self):
        self.assertEqual(guard.extract_role("faber2: another fix", ""), "Faber")
        self.assertEqual(guard.extract_role("TESTAROSSA1: verify it", ""), "Testarossa")

    def test_falls_back_to_prompt(self):
        role = guard.extract_role("some unrelated description",
                                   "You are MarcoPolo, doing reconnaissance.")
        self.assertEqual(role, "MarcoPolo")

    def test_unrecognised_role_returns_none(self):
        self.assertIsNone(guard.extract_role("code-reviewer: look at this", "You are a helpful reviewer."))

    def test_no_role_anywhere_returns_none(self):
        self.assertIsNone(guard.extract_role("fix the bug", "Please fix this bug in the code."))


class TestDecide(unittest.TestCase):
    def test_faber_without_model_denies(self):
        decision, reason = guard.decide("Faber", {}, [])
        self.assertEqual(decision, "deny")
        self.assertIn("Faber", reason)
        self.assertIn("model", reason)

    def test_faber_with_model_allows(self):
        decision, reason = guard.decide("Faber", {"model": "sonnet"}, [])
        self.assertIsNone(decision)
        self.assertIsNone(reason)

    def test_gaudi_without_model_allows(self):
        decision, reason = guard.decide("Gaudi", {}, [])
        self.assertIsNone(decision)

    def test_second_dispatch_same_role_asks(self):
        prior = [{"role": "Faber", "description": "first task", "timestamp": "2026-09-15T10:00:00+00:00"}]
        decision, reason = guard.decide("Faber", {"model": "sonnet"}, prior)
        self.assertEqual(decision, "ask")
        self.assertIn("Faber", reason)
        self.assertIn("first task", reason)
        self.assertIn("2026-09-15T10:00:00+00:00", reason)

    def test_different_role_in_register_does_not_ask(self):
        prior = [{"role": "MarcoPolo", "description": "recon", "timestamp": "2026-09-15T10:00:00+00:00"}]
        decision, reason = guard.decide("Faber", {"model": "sonnet"}, prior)
        self.assertIsNone(decision)


class TestRegisterIO(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_file_returns_empty(self):
        self.assertEqual(guard.load_register(self.tmp / "nope.jsonl"), [])

    def test_append_then_load_round_trips(self):
        path = self.tmp / "s.jsonl"
        guard.append_register(path, {"role": "Faber", "description": "x", "timestamp": "t"})
        guard.append_register(path, {"role": "Gaudi", "description": "y", "timestamp": "t2"})
        entries = guard.load_register(path)
        self.assertEqual([e["role"] for e in entries], ["Faber", "Gaudi"])

    def test_corrupt_register_fails_open(self):
        path = self.tmp / "corrupt.jsonl"
        path.write_text("{not json\n{\"role\": \"Faber\", \"description\": \"ok line\", \"timestamp\": \"t\"}\n",
                         encoding="utf-8")
        entries = guard.load_register(path)
        # the corrupt line is skipped, the valid one still comes through
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["role"], "Faber")

    def test_totally_unreadable_register_fails_open(self):
        # a directory where a file is expected raises OSError on read_text
        path = self.tmp / "adir.jsonl"
        path.mkdir()
        self.assertEqual(guard.load_register(path), [])


class TestEndToEnd(unittest.TestCase):
    """Runs the hook as the real subprocess Claude Code would invoke, stdin in,
    stdout/exit code out, against an isolated register directory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_faber_without_model_is_denied(self):
        stdin = agent_input(model=None)
        # simulate an omitted model by dropping the key entirely
        payload = json.loads(stdin)
        del payload["tool_input"]["model"]
        result = run_hook(json.dumps(payload), self.tmp)
        self.assertEqual(result.returncode, 0)
        out = json.loads(result.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("model", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_faber_with_model_is_allowed_silently(self):
        result = run_hook(agent_input(model="sonnet"), self.tmp)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_gaudi_on_top_of_range_is_allowed(self):
        result = run_hook(agent_input(description="Gaudi: design the migration",
                                       prompt="You are Gaudi, the architect.",
                                       model="opus"), self.tmp)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_second_faber_dispatch_same_session_asks_and_names_first(self):
        run_hook(agent_input(session_id="sess-a", description="Faber: issue 98 distributors", model="sonnet"), self.tmp)
        result = run_hook(agent_input(session_id="sess-a", description="Faber: issue 101 quotations", model="sonnet"), self.tmp)
        out = json.loads(result.stdout)
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "ask")
        self.assertIn("issue 98 distributors", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_same_role_different_session_does_not_ask(self):
        run_hook(agent_input(session_id="sess-a", description="Faber: issue 98 distributors", model="sonnet"), self.tmp)
        result = run_hook(agent_input(session_id="sess-b", description="Faber: issue 101 quotations", model="sonnet"), self.tmp)
        self.assertEqual(result.stdout.strip(), "")

    def test_unrecognised_role_is_allowed_untouched(self):
        result = run_hook(agent_input(description="code-reviewer: look at this diff",
                                       prompt="You are a meticulous code reviewer.",
                                       model=None), self.tmp)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_malformed_stdin_fails_open(self):
        result = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, {str(HOOK_DIR)!r}); "
                                    f"import guard_agent_dispatch as g; sys.exit(g.main())"],
            input="{not valid json", capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")

    def test_unwritable_register_still_allows(self):
        # point REGISTER_DIR at a path that can't be created (a file standing where
        # a directory is expected), and confirm the call is still allowed.
        blocker = self.tmp / "blocker"
        blocker.write_text("x", encoding="utf-8")
        bad_register_dir = blocker / "agent-dispatch-register"
        result = run_hook(agent_input(model="sonnet"), bad_register_dir)
        self.assertEqual(result.returncode, 0)
        # allowed (no deny/ask JSON), even though the register write failed
        if result.stdout.strip():
            out = json.loads(result.stdout)
            self.assertNotEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
