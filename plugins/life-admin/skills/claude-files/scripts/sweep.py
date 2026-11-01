#!/usr/bin/env python3
"""
sweep.py - find what Claude left lying around and archive it in one place.

Looks through the folders given for Claude's leftovers and moves them into
<home>/Archive/<YYYY-MM>/, keeping where each came from. Nothing is deleted.
Every run writes an undo log.

What counts as a leftover:
  - folders named "Claude outputs" / "claude-output(s)" / "claude-scratch"
  - packaged plugins (*.plugin) outside a repo's dist/ folder
  - _tidy folders (file-cleanup plans) older than --days
  - git leftovers Claude couldn't delete: .git/stale-*lock*, .git/push-*.bundle,
    .git/objects/**/tmp_obj_*
  - loose files at a folder's top level named claude-*, *-claude-output.* or
    starting with "Claude " that are older than --days

Usage:
  python3 sweep.py scan  HOME FOLDER [FOLDER ...] [--days 14] [--out plan.json]
  python3 sweep.py apply plan.json
  python3 sweep.py undo  HOME/Archive/<YYYY-MM>/undo-<stamp>.json

HOME is the one folder Claude's work belongs in (for example ~/Documents/Claude).
Standard library only.
"""
import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

OUTPUT_DIRS = {"claude outputs", "claude-outputs", "claude-output", "claude-scratch"}
SKIP_DIRS = {"node_modules", ".Trash", "Library", "Archive"}
LOOSE_PATTERNS = ["claude-*", "*-claude-output.*", "Claude *"]
GIT_PATTERNS = ["stale-*lock*", "push-*.bundle"]
MAX_DEPTH = 4


def age_days(p):
    try:
        return (time.time() - p.lstat().st_mtime) / 86400
    except OSError:
        return 0


def size_of(p):
    if p.is_file() or p.is_symlink():
        try:
            return p.lstat().st_size
        except OSError:
            return 0
    total = 0
    for dirpath, _, files in os.walk(p):
        for f in files:
            try:
                total += os.lstat(os.path.join(dirpath, f)).st_size
            except OSError:
                pass
    return total


def tracked_by_git(p):
    """True when p (or anything inside it) is committed to a git repo: then it
    is project content, not a leftover, whatever it is called."""
    repo = next((q for q in [p.parent, *p.parents] if (q / ".git").exists()), None)
    if repo is None:
        return False
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "ls-files", "--", str(p.relative_to(repo))],
            capture_output=True, text=True, timeout=20,
        ).stdout
    except (OSError, subprocess.SubprocessError, ValueError):
        return True  # can't tell, so leave it alone
    return bool(out.strip())


def git_leftovers(git_dir):
    found = []
    for pattern in GIT_PATTERNS:
        found += [(p, "git leftover") for p in git_dir.glob(pattern)]
    objects = git_dir / "objects"
    if objects.is_dir():
        found += [(p, "git temp object") for p in objects.glob("*/tmp_obj_*")]
    return found


def scan_folder(root, days, home):
    found = []
    root_depth = len(root.parts)
    for dirpath, dirnames, filenames in os.walk(root):
        here = Path(dirpath)
        if home in here.parents or here == home:
            dirnames[:] = []
            continue
        depth = len(here.parts) - root_depth
        keep = []
        for d in dirnames:
            p = here / d
            if d == ".git":
                found += git_leftovers(p)
            elif d.lower() in OUTPUT_DIRS:
                if not tracked_by_git(p):
                    found.append((p, "Claude output folder"))
            elif d == "_tidy" and age_days(p) > days:
                found.append((p, "old cleanup plan"))
            elif d in SKIP_DIRS or d.startswith(".") or d.endswith((".app", ".photoslibrary")):
                continue
            elif depth < MAX_DEPTH:
                keep.append(d)
        dirnames[:] = keep
        for f in filenames:
            p = here / f
            if f.endswith(".plugin") and "dist" not in p.parts and not tracked_by_git(p):
                found.append((p, "packaged plugin"))
            elif depth == 0 and age_days(p) > days and any(
                fnmatch.fnmatch(f, pat) for pat in LOOSE_PATTERNS
            ):
                found.append((p, "loose Claude file"))
    return found


def scan(home, folders, days):
    home = home.expanduser().resolve()
    items = []
    seen = set()
    for folder in folders:
        root = folder.expanduser().resolve()
        if not root.is_dir():
            continue
        for p, why in scan_folder(root, days, home):
            if p in seen:
                continue
            seen.add(p)
            items.append({"path": str(p), "reason": why, "root": str(root), "size": size_of(p)})
    month = datetime.now().strftime("%Y-%m")
    return {"home": str(home), "archive": str(home / "Archive" / month), "items": items,
            "scanned_at": datetime.now().isoformat(timespec="seconds")}


def dest_for(archive, src, root=None):
    # Keep the origin readable: Archive/2026-11/Desktop/Claude outputs
    try:
        rel = src.relative_to(root) if root else Path(*src.parts[-2:])
        dest = archive / Path(root).name / rel if root else archive / rel
    except ValueError:
        dest = archive / src.name
    i = 2
    while dest.exists():
        dest = dest.with_name(f"{dest.stem} ({i}){dest.suffix}")
        i += 1
    return dest


def apply(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    archive = Path(plan["archive"])
    archive.mkdir(parents=True, exist_ok=True)
    log = archive / f"undo-{datetime.now():%Y%m%d-%H%M%S}.json"
    moved, skipped = [], []
    for item in plan["items"]:
        src = Path(item["path"])
        if not (src.exists() or src.is_symlink()):
            continue
        dest = dest_for(archive, src, item.get("root"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dest))
        except (OSError, shutil.Error) as e:
            # Typically a cloud file that isn't downloaded, or a folder the
            # original can't be removed from. The original stays where it is.
            skipped.append({"path": str(src), "why": str(e).splitlines()[0][:200]})
            continue
        moved.append({"from": str(src), "reason": item["reason"], "to": str(dest)})
        log.write_text(json.dumps({"moves": moved}, indent=1))
    print(json.dumps({"archive": str(archive), "moved": len(moved), "skipped": skipped,
                      "undo_log": str(log) if moved else None}, indent=1))


def undo(log_path):
    log = json.loads(Path(log_path).read_text())
    restored = 0
    for m in reversed(log["moves"]):
        src, dest = Path(m["to"]), Path(m["from"])
        if src.exists() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            restored += 1
    Path(log_path).rename(Path(log_path).with_suffix(".undone.json"))
    print(json.dumps({"restored": restored, "of": len(log["moves"])}))


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("home")
    s.add_argument("folders", nargs="+")
    s.add_argument("--days", type=int, default=14)
    s.add_argument("--out")
    a = sub.add_parser("apply")
    a.add_argument("plan")
    u = sub.add_parser("undo")
    u.add_argument("log")
    args = ap.parse_args()
    if args.cmd == "scan":
        home = Path(args.home)
        plan = scan(home, [Path(f) for f in args.folders], args.days)
        out = Path(args.out) if args.out else home.expanduser() / "sweep-plan.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=1))
        by = {}
        for i in plan["items"]:
            b = by.setdefault(i["reason"], {"count": 0, "bytes": 0})
            b["count"] += 1
            b["bytes"] += i["size"]
        print(json.dumps({"plan": str(out), "archive": plan["archive"],
                          "found": {k: f'{v["count"]} ({human(v["bytes"])})' for k, v in by.items()},
                          "items": [f'{i["reason"]}: {i["path"]}' for i in plan["items"][:40]]}, indent=1))
    elif args.cmd == "apply":
        apply(args.plan)
    else:
        undo(args.log)


if __name__ == "__main__":
    sys.exit(main())
