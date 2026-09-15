#!/usr/bin/env python3
"""
Tests for guard_agent_dispatch.py, install.py's skill-linking, and
inject_doctrine.py's drift check.

No test convention exists in this repo yet (no unittest/pytest usage found anywhere
under harnessing/ or devaing/'s own scripts) -- this is one stdlib-only unittest
file for the whole hooks+installer surface, extended rather than duplicated as
each piece was added, run directly:

  python harnessing/hooks/test_guard_agent_dispatch.py

Every test that touches "the machine" points HOME/USERPROFILE (or Path.home()
via mock) at a temporary directory first. Nothing here ever writes to the real
~/.claude.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOOK_DIR = Path(__file__).resolve().parent
HARNESSING_DIR = HOOK_DIR.parent
sys.path.insert(0, str(HOOK_DIR))
sys.path.insert(0, str(HARNESSING_DIR))

import guard_agent_dispatch as guard  # noqa: E402
import install as harnessing_install  # noqa: E402

INJECT_DOCTRINE = HOOK_DIR / "inject_doctrine.py"
CONDENSED = HARNESSING_DIR / "doctrine" / "condensed.md"
INSTALL_PY = HARNESSING_DIR / "install.py"


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


class TestSkillLinking(unittest.TestCase):
    """install.py's install-as-a-link machinery: _skill_state, _install_one_skill,
    _remove_installed_skill. Real filesystem, temp directories only -- never the
    real ~/.claude.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="linktest_"))
        self.src = self.tmp / "src_skill"
        self.src.mkdir()
        (self.src / "SKILL.md").write_text("v1", encoding="utf-8")
        self.dest = self.tmp / "dest" / "myskill"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _content(self, path):
        return (path / "SKILL.md").read_text(encoding="utf-8")

    def test_link_created_from_absent(self):
        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "written")
        self.assertTrue(self.dest.is_symlink() or harnessing_install._is_junction(self.dest))
        self.assertEqual(self._content(self.dest), "v1")
        # and it is live: editing the source is visible with no reinstall
        (self.src / "SKILL.md").write_text("v2", encoding="utf-8")
        self.assertEqual(self._content(self.dest), "v2")

    def test_check_on_absent_reports_and_writes_nothing(self):
        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=True)
        self.assertEqual(step.status, "missing")
        self.assertFalse(self.dest.exists())

    def test_second_run_is_ok_linked_and_resolving(self):
        harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "ok")
        self.assertIn("linked and resolving", step.detail)

    def test_existing_copy_current_content_is_replaced_with_a_link(self):
        self.dest.mkdir(parents=True)
        (self.dest / "SKILL.md").write_text("v1", encoding="utf-8")  # matches src
        state, _ = harnessing_install._skill_state(self.dest, self.src)
        self.assertEqual(state, "copied_current")

        check_step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=True)
        self.assertEqual(check_step.status, "missing")
        self.assertIn("copied and current", check_step.detail)
        self.assertTrue(self.dest.is_dir() and not self.dest.is_symlink())  # --check wrote nothing

        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "updated")
        self.assertTrue(self.dest.is_symlink() or harnessing_install._is_junction(self.dest))

    def test_existing_copy_stale_content_is_replaced_with_a_link(self):
        self.dest.mkdir(parents=True)
        (self.dest / "SKILL.md").write_text("an old copy, repo moved on", encoding="utf-8")
        state, _ = harnessing_install._skill_state(self.dest, self.src)
        self.assertEqual(state, "copied_stale")

        check_step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=True)
        self.assertIn("copied and stale", check_step.detail)

        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "updated")
        self.assertEqual(self._content(self.dest), "v1")

    def test_source_missing_leaves_existing_copy_untouched(self):
        self.dest.mkdir(parents=True)
        (self.dest / "SKILL.md").write_text("whatever was copied here", encoding="utf-8")
        shutil.rmtree(self.src)
        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "missing")
        self.assertIn("leaving the existing", step.detail)
        self.assertTrue(self.dest.is_dir() and not self.dest.is_symlink())
        self.assertEqual(self._content(self.dest), "whatever was copied here")

    def test_source_missing_leaves_existing_link_untouched(self):
        harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        shutil.rmtree(self.src)
        step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "missing")
        # the (now dangling) link must still be there -- never removed just because
        # this run's source vanished
        self.assertTrue(self.dest.is_symlink() or harnessing_install._is_junction(self.dest))

    def test_dangling_link_is_detected_and_relinked_once_source_returns(self):
        harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        shutil.rmtree(self.src)
        state, _ = harnessing_install._skill_state(self.dest, self.src)
        self.assertEqual(state, "dangling")
        check_step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=True)
        self.assertEqual(check_step.status, "missing")
        self.assertIn("dangling", check_step.detail)

        # point dest at a different (new) source path -- a real relink, not a
        # junction/symlink resolving again purely because the old path reappeared
        new_src = self.tmp / "new_src"
        new_src.mkdir()
        (new_src / "SKILL.md").write_text("v-new", encoding="utf-8")
        step = harnessing_install._install_one_skill("myskill", new_src, self.dest, check=False)
        self.assertEqual(step.status, "updated")  # replacing a dangling link, not a fresh install
        self.assertEqual(self._content(self.dest), "v-new")

    def test_obstruction_is_never_removed(self):
        self.dest.parent.mkdir(parents=True)
        self.dest.write_text("not a skill, just a stray file", encoding="utf-8")
        for check in (True, False):
            step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=check)
            self.assertEqual(step.status, "missing")
            self.assertIn("not touching it", step.detail)
        self.assertTrue(self.dest.is_file())
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "not a skill, just a stray file")

    def test_fallback_to_copy_when_both_linking_methods_fail(self):
        with mock.patch.object(os, "symlink", side_effect=OSError("no privilege")), \
             mock.patch.object(harnessing_install.subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="mklink denied")
            method, note = harnessing_install._link_skill(self.src, self.dest)
        self.assertEqual(method, "copy")
        self.assertIn("no privilege", note)
        self.assertTrue(self.dest.is_dir())
        self.assertFalse(self.dest.is_symlink())
        self.assertFalse(harnessing_install._is_junction(self.dest))
        self.assertEqual(self._content(self.dest), "v1")

    def test_install_one_skill_reports_fallback_to_copy_honestly(self):
        with mock.patch.object(os, "symlink", side_effect=OSError("no privilege")), \
             mock.patch.object(harnessing_install.subprocess, "run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="mklink denied")
            step = harnessing_install._install_one_skill("myskill", self.src, self.dest, check=False)
        self.assertEqual(step.status, "written")
        self.assertIn("copied", step.detail)
        self.assertIn("linking failed", step.detail)


class TestInstallSkillsIntegration(unittest.TestCase):
    """install_skills()/--check against a fake HOME, end to end: confirms the
    real machine ends up with links, not copies, and that --check distinguishes
    the five states in its own output.
    """

    def setUp(self):
        self.fake_home = Path(tempfile.mkdtemp(prefix="fakehome_link_"))
        (self.fake_home / ".claude").mkdir(parents=True)
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.fake_home)
        self.env["USERPROFILE"] = str(self.fake_home)

    def tearDown(self):
        shutil.rmtree(self.fake_home, ignore_errors=True)

    def _run(self, *args):
        return subprocess.run([sys.executable, str(INSTALL_PY), *args], env=self.env,
                               capture_output=True, text=True)

    def test_fresh_install_produces_links_not_copies(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for name in harnessing_install.SKILL_NAMES:
            dest = self.fake_home / ".claude" / "skills" / name
            self.assertTrue(dest.is_symlink() or harnessing_install._is_junction(dest),
                             f"{name} should be installed as a link, not a copy")

    def test_check_reports_all_five_distinct_states(self):
        # absent
        r = self._run("--check")
        self.assertIn("would link", r.stdout)

        # linked and resolving
        self._run()
        r = self._run("--check")
        self.assertIn("linked and resolving", r.stdout)

        # copied and current, then stale
        name = harnessing_install.SKILL_NAMES[0]
        dest = self.fake_home / ".claude" / "skills" / name
        src = harnessing_install.SKILLS_DIR / name
        harnessing_install._remove_installed_skill(dest)
        dest.mkdir(parents=True)
        for f in src.glob("*.md"):
            shutil.copyfile(f, dest / f.name)
        r = self._run("--check")
        self.assertIn("copied and current", r.stdout)

        (dest / next(src.glob("*.md")).name).write_text("stale content", encoding="utf-8")
        r = self._run("--check")
        self.assertIn("copied and stale", r.stdout)

        # dangling and obstructed are exercised against temp directories in
        # TestSkillLinking -- forcing "dangling" here would mean deleting a real
        # skill directory out of this checkout, which is not a trade worth making
        # just to repeat coverage this suite already has. Nothing above touched
        # anything outside self.fake_home, which tearDown removes wholesale.


class TestDriftCheck(unittest.TestCase):
    """inject_doctrine.py's drift check: repairs hooks+links silently, reports
    (never fixes) doctrine-pointer drift, fails open. All against fake homes.
    """

    def setUp(self):
        self.fake_home = Path(tempfile.mkdtemp(prefix="drift_home_"))
        (self.fake_home / ".claude").mkdir(parents=True)
        self.project = Path(tempfile.mkdtemp(prefix="drift_proj_"))

    def tearDown(self):
        shutil.rmtree(self.fake_home, ignore_errors=True)
        shutil.rmtree(self.project, ignore_errors=True)

    def _run_hook(self, cwd_for_stdin=None, condensed=CONDENSED):
        env = dict(os.environ)
        env["HOME"] = str(self.fake_home)
        env["USERPROFILE"] = str(self.fake_home)
        stdin = json.dumps({"cwd": str(cwd_for_stdin)}) if cwd_for_stdin else ""
        r = subprocess.run([sys.executable, str(INJECT_DOCTRINE), str(condensed)], input=stdin,
                            capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _install_pointer_for_real(self):
        env = dict(os.environ)
        env["HOME"] = str(self.fake_home)
        env["USERPROFILE"] = str(self.fake_home)
        r = subprocess.run([sys.executable, str(INSTALL_PY), "--path", str(self.project)],
                            cwd=str(self.project), env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_bare_home_repairs_hooks_and_links_reports_missing_pointer(self):
        out = self._run_hook(self.project)
        self.assertIn("systemMessage", out)
        self.assertIn("repaired", out["systemMessage"])
        self.assertIn("no doctrine pointer reaches", out["systemMessage"])
        self.assertIn("harnessing install drift", out["hookSpecificOutput"]["additionalContext"])
        self.assertTrue((self.fake_home / ".claude" / "hooks" / "harnessing_guard_agent_dispatch.py").is_file())
        self.assertTrue((self.fake_home / ".claude" / "skills" / "harnessing-init").is_dir())

    def test_nothing_drifted_is_silent(self):
        self._run_hook(self.project)  # first pass repairs hooks/links
        self._install_pointer_for_real()
        out = self._run_hook(self.project)
        self.assertNotIn("systemMessage", out)
        self.assertEqual(out["hookSpecificOutput"]["additionalContext"], CONDENSED.read_text(encoding="utf-8"))

    def test_stale_doctrine_pointer_is_reported_never_rewritten(self):
        self._run_hook(self.project)
        self._install_pointer_for_real()
        claude_md = self.project / "CLAUDE.md"
        original = claude_md.read_text(encoding="utf-8")
        corrupted = original.replace("harnessing doctrine", "harnessing doctrine (hand-edited)")
        claude_md.write_text(corrupted, encoding="utf-8")

        out = self._run_hook(self.project)
        self.assertIn("systemMessage", out)
        self.assertIn("out of date", out["systemMessage"])
        self.assertIn("install.py", out["systemMessage"])
        self.assertIn("--path", out["systemMessage"])
        self.assertEqual(claude_md.read_text(encoding="utf-8"), corrupted,
                          "the hook must never rewrite the doctrine pointer itself")

    def test_missing_hook_registration_is_silently_repaired(self):
        self._run_hook(self.project)
        self._install_pointer_for_real()
        settings_path = self.fake_home / ".claude" / "settings.json"
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
        del settings["hooks"]["PreToolUse"]
        settings_path.write_text(json.dumps(settings), encoding="utf-8")

        out = self._run_hook(self.project)
        self.assertIn("systemMessage", out)
        self.assertIn("PreToolUse", out["systemMessage"])
        self.assertIn("repaired", out["systemMessage"])
        settings_after = json.loads(settings_path.read_text(encoding="utf-8"))
        self.assertIn("PreToolUse", settings_after["hooks"])

        out2 = self._run_hook(self.project)
        self.assertNotIn("systemMessage", out2, "repair must be idempotent: nothing left to fix")

    def test_fails_open_when_install_py_is_not_alongside_condensed(self):
        lonely = Path(tempfile.mkdtemp(prefix="lonely_"))
        try:
            lonely_doctrine = lonely / "doctrine"
            lonely_doctrine.mkdir()
            lonely_condensed = lonely_doctrine / "condensed.md"
            lonely_condensed.write_text("some doctrine text", encoding="utf-8")
            out = self._run_hook(self.project, condensed=lonely_condensed)
            self.assertNotIn("systemMessage", out)
            self.assertEqual(out["hookSpecificOutput"]["additionalContext"], "some doctrine text")
        finally:
            shutil.rmtree(lonely, ignore_errors=True)

    def test_malformed_stdin_fails_open(self):
        env = dict(os.environ)
        env["HOME"] = str(self.fake_home)
        env["USERPROFILE"] = str(self.fake_home)
        r = subprocess.run([sys.executable, str(INJECT_DOCTRINE), str(CONDENSED)], input="{not json",
                            capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        out = json.loads(r.stdout)
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "SessionStart")


if __name__ == "__main__":
    unittest.main()
