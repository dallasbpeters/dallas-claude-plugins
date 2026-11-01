"""Tests for tidy.py. Run: python3 -m unittest discover -s <this folder>"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

TIDY = Path(__file__).with_name("tidy.py")


def run(*args):
    out = subprocess.run([sys.executable, str(TIDY), *map(str, args)], capture_output=True, text=True, check=True)
    return out.stdout


def age(path, days):
    t = time.time() - days * 86400
    os.utime(path, (t, t))


def snapshot(root):
    """Every file under root (except our own _tidy folder) with its contents."""
    return {
        str(p.relative_to(root)): p.read_bytes()
        for p in root.rglob("*")
        if p.is_file() and "_tidy" not in p.parts
    }


class TidyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        r = self.root
        (r / "a.txt").write_text("hello")
        (r / "a (1).txt").write_text("hello")
        age(r / "a (1).txt", 0)
        age(r / "a.txt", 10)
        (r / "photo.jpg").write_text("img")
        (r / "Screenshot 2026-01-01 at 9.00.png").write_text("shot")
        (r / "setup.dmg").write_text("installer")
        age(r / "setup.dmg", 60)
        (r / "new.dmg").write_text("fresh installer")
        (r / "empty.txt").write_text("")
        (r / ".DS_Store").write_text("x")
        (r / "half.crdownload").write_text("partial")
        (r / "old.pdf").write_text("old doc")
        age(r / "old.pdf", 400)
        (r / "Clients" / "acme").mkdir(parents=True)
        (r / "Clients" / "acme" / "brief.md").write_text("their system")
        (r / "Clients" / "brief copy.md").write_text("their system")
        age(r / "Clients" / "acme" / "brief.md", 30)
        (r / "Thing.app" / "Contents").mkdir(parents=True)
        (r / "Thing.app" / "Contents" / "bin").write_text("app")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self):
        run("scan", self.root)
        return json.loads((self.root / "_tidy" / "plan.json").read_text())

    def moves(self):
        return {a["from"]: (a["group"], a["to"]) for a in self.plan()["actions"]}

    def test_scan_changes_nothing(self):
        before = snapshot(self.root)
        self.plan()
        self.assertEqual(snapshot(self.root), before)

    def test_keeps_the_oldest_duplicate(self):
        m = self.moves()
        self.assertEqual(m["a (1).txt"][0], "duplicates")
        self.assertEqual(m["a.txt"][0], "sort")
        # Copies inside folders are left alone unless --deep-duplicates.
        self.assertNotIn("Clients/brief copy.md", m)
        self.assertNotIn("Clients/acme/brief.md", m)

    def test_deep_duplicates_flag(self):
        run("scan", self.root, "--deep-duplicates")
        plan = json.loads((self.root / "_tidy" / "plan.json").read_text())
        m = {a["from"]: a["group"] for a in plan["actions"]}
        self.assertEqual(m["Clients/brief copy.md"], "duplicates")

    def test_keeps_localized(self):
        (self.root / ".localized").write_text("")
        self.assertNotIn(".localized", self.moves())

    def test_groups(self):
        m = self.moves()
        self.assertEqual(m["empty.txt"][0], "junk")
        self.assertEqual(m[".DS_Store"][0], "junk")
        self.assertEqual(m["half.crdownload"][0], "junk")
        self.assertEqual(m["setup.dmg"][0], "installers")
        # An installer from this week is sorted, not flagged.
        self.assertEqual(m["new.dmg"], ("sort", "Installers/new.dmg"))
        self.assertTrue(m["Screenshot 2026-01-01 at 9.00.png"][1].startswith("Screenshots/"))
        self.assertEqual(m["photo.jpg"], ("sort", "Images/photo.jpg"))
        self.assertRegex(m["old.pdf"][1], r"^Documents/\d{4}/old\.pdf$")

    def test_leaves_their_folders_and_apps_alone(self):
        m = self.moves()
        self.assertFalse(any(k.startswith("Thing.app") for k in m))
        self.assertNotIn("Clients/acme/brief.md", m)

    def test_only_moves_into_to_delete_never_deletes(self):
        before = snapshot(self.root)
        plan = self.root / "_tidy" / "plan.json"
        run("scan", self.root)
        out = json.loads(run("apply", plan))
        after = snapshot(self.root)
        # Same contents, same count: nothing was removed, only renamed.
        self.assertEqual(sorted(before.values()), sorted(after.values()))
        self.assertTrue((self.root / "_to_delete" / "duplicates" / "a (1).txt").exists())
        self.assertGreater(out["moved"], 0)

    def test_only_flag_limits_groups(self):
        run("scan", self.root)
        run("apply", self.root / "_tidy" / "plan.json", "--only", "junk")
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertFalse((self.root / "empty.txt").exists())

    def test_undo_restores_everything(self):
        before = snapshot(self.root)
        run("scan", self.root)
        out = json.loads(run("apply", self.root / "_tidy" / "plan.json"))
        undone = json.loads(run("undo", out["undo_log"]))
        self.assertEqual(undone["restored"], undone["of"])
        self.assertEqual(snapshot(self.root), before)

    def test_name_clash_gets_a_number(self):
        (self.root / "Images").mkdir()
        (self.root / "Images" / "photo.jpg").write_text("different")
        run("scan", self.root)
        run("apply", self.root / "_tidy" / "plan.json", "--only", "sort")
        self.assertEqual((self.root / "Images" / "photo.jpg").read_text(), "different")
        self.assertEqual((self.root / "Images" / "photo (2).jpg").read_text(), "img")


if __name__ == "__main__":
    unittest.main()


class ToHomeTest(unittest.TestCase):
    """--to-home: Downloads/Desktop are emptied into the home folder's own folders."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        (self.home / "Pictures").mkdir()
        (self.home / "Pictures" / "photo.jpg").write_text("already here")
        self.root = self.home / "Downloads"
        self.root.mkdir()
        r = self.root
        (r / "photo.jpg").write_text("img")
        (r / "clip.mov").write_text("video")
        (r / "budget.xlsx").write_text("sheet")
        (r / "old.pdf").write_text("old doc")
        age(r / "old.pdf", 400)
        (r / "Screenshot 2026-01-01 at 9.00.png").write_text("shot")
        (r / "logo.psd").write_text("design")
        (r / ".DS_Store").write_text("x")
        (r / "Clients").mkdir()
        (r / "Clients" / "brief.md").write_text("their system")
        self.env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home)}

    def tearDown(self):
        self.tmp.cleanup()

    def tidy(self, *args):
        out = subprocess.run([sys.executable, str(TIDY), *map(str, args)], capture_output=True, text=True, check=True, env=self.env)
        return out.stdout

    def test_sorts_into_home_folders_and_undoes(self):
        self.tidy("scan", self.root, "--to-home")
        plan_path = self.home / ".tidy" / "Downloads" / "plan.json"
        self.assertFalse((self.root / "_tidy").exists())
        to = {a["from"]: a["to"] for a in json.loads(plan_path.read_text())["actions"]}
        self.assertEqual(to["photo.jpg"], str(self.home / "Pictures" / "photo.jpg"))
        self.assertEqual(to["clip.mov"], str(self.home / "Movies" / "clip.mov"))
        self.assertEqual(to["budget.xlsx"], str(self.home / "Documents" / "budget.xlsx"))
        self.assertEqual(to["old.pdf"], str(self.home / "Documents" / "old.pdf"))  # no year folder
        self.assertEqual(to["logo.psd"], str(self.home / "Design" / "logo.psd"))
        self.assertTrue(to["Screenshot 2026-01-01 at 9.00.png"].startswith(str(self.home / "Screenshots")))
        self.assertEqual(to[".DS_Store"], str(self.home / "_to_delete" / "junk" / ".DS_Store"))
        self.assertNotIn("Clients/brief.md", to)

        result = json.loads(self.tidy("apply", plan_path))
        self.assertEqual((self.home / "Pictures" / "photo (2).jpg").read_text(), "img")
        self.assertEqual((self.home / "Pictures" / "photo.jpg").read_text(), "already here")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ["Clients"])

        self.tidy("undo", result["undo_log"])
        self.assertEqual((self.root / "photo.jpg").read_text(), "img")
        self.assertEqual((self.root / "clip.mov").read_text(), "video")
        self.assertEqual((self.home / "Pictures" / "photo.jpg").read_text(), "already here")
        self.assertFalse((self.home / "Pictures" / "photo (2).jpg").exists())

    def test_refuses_to_sort_home_itself(self):
        out = subprocess.run([sys.executable, str(TIDY), "scan", self.home, "--to-home"], capture_output=True, text=True, env=self.env)
        self.assertNotEqual(out.returncode, 0)

