"""Tests for sweep.py. Run: python3 -m unittest discover -s <this folder>"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SWEEP = Path(__file__).with_name("sweep.py")


def run(*args):
    return subprocess.run([sys.executable, str(SWEEP), *map(str, args)], capture_output=True, text=True, check=True).stdout


def old(p, days=30):
    t = time.time() - days * 86400
    os.utime(p, (t, t))


class SweepTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = Path(self.tmp.name)
        self.home = r / "Documents" / "Claude"
        self.desk = r / "Desktop"
        self.dev = r / "Development"
        (self.desk / "Claude outputs").mkdir(parents=True)
        (self.desk / "Claude outputs" / "a.png").write_text("x")
        (self.desk / "My Project").mkdir()
        (self.desk / "My Project" / "notes.md").write_text("mine")
        (self.desk / "claude-scratch.txt").write_text("old")
        old(self.desk / "claude-scratch.txt")
        (self.desk / "claude-today.txt").write_text("new")
        (self.desk / "_tidy").mkdir()
        old(self.desk / "_tidy")
        git = self.dev / "site" / ".git"
        (git / "objects" / "ab").mkdir(parents=True)
        (git / "objects" / "ab" / "tmp_obj_123").write_text("t")
        (git / "objects" / "ab" / "realobject").write_text("keep")
        (git / "stale-HEAD-lock-1").write_text("")
        (git / "push-abc.bundle").write_text("b")
        (git / "HEAD").write_text("ref")
        (self.dev / "site" / "dist").mkdir()
        (self.dev / "site" / "dist" / "keep.plugin").write_text("built")
        (self.dev / "life-admin.plugin").write_text("p")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        run("scan", self.home, self.desk, self.dev, "--out", self.home / "plan.json")
        return json.loads((self.home / "plan.json").read_text())

    def test_finds_only_leftovers(self):
        found = {Path(i["path"]).name: i["reason"] for i in self.plan()["items"]}
        self.assertEqual(found["Claude outputs"], "Claude output folder")
        self.assertEqual(found["claude-scratch.txt"], "loose Claude file")
        self.assertEqual(found["_tidy"], "old cleanup plan")
        self.assertEqual(found["tmp_obj_123"], "git temp object")
        self.assertIn("stale-HEAD-lock-1", found)
        self.assertIn("push-abc.bundle", found)
        self.assertEqual(found["life-admin.plugin"], "packaged plugin")
        for kept in ("My Project", "notes.md", "claude-today.txt", "realobject", "HEAD", "keep.plugin"):
            self.assertNotIn(kept, found)

    def test_scan_moves_nothing(self):
        self.plan()
        self.assertTrue((self.desk / "Claude outputs" / "a.png").exists())

    def test_apply_archives_and_undo_restores(self):
        self.plan()
        out = json.loads(run("apply", self.home / "plan.json"))
        self.assertGreater(out["moved"], 0)
        self.assertFalse((self.desk / "Claude outputs").exists())
        self.assertTrue((self.dev / "site" / ".git" / "HEAD").exists())
        archived = list(Path(out["archive"]).rglob("a.png"))
        self.assertEqual(len(archived), 1)
        # Filed under the folder it came from.
        self.assertEqual(archived[0].parent.parent.name, "Desktop")
        run("undo", out["undo_log"])
        self.assertTrue((self.desk / "Claude outputs" / "a.png").exists())
        self.assertTrue((self.dev / "site" / ".git" / "objects" / "ab" / "tmp_obj_123").exists())

    def test_leaves_git_tracked_output_folders(self):
        repo = self.dev / "site"
        (repo / "Claude outputs").mkdir()
        (repo / "Claude outputs" / "shot.png").write_text("x")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        # The fake .git above isn't a real repo; re-init made it one.
        subprocess.run(["git", "-C", str(repo), "add", "Claude outputs"], check=True)
        found = [i["path"] for i in self.plan()["items"]]
        self.assertFalse(any(p.endswith("site/Claude outputs") for p in found))

    def test_never_scans_inside_home(self):
        (self.home / "Claude outputs").mkdir(parents=True)
        found = [i["path"] for i in self.plan()["items"]]
        self.assertFalse(any(str(self.home) in p for p in found))


if __name__ == "__main__":
    unittest.main()
