#!/usr/bin/env python3
"""
tidy.py - look at a messy folder, propose a cleanup, apply it, undo it.

Nothing is ever deleted. Files are only moved:
  - into sorted folders (Images, Documents, ...), or, with --to-home, into the
    home folder's own folders (~/Pictures, ~/Documents, ~/Movies, ...), or
  - into a "_to_delete" folder the person empties themselves.
Every move is written to an undo log, so `undo` puts everything back.

Usage:
  python3 tidy.py scan  FOLDER [--to-home] [--out plan.json] [--old-days 180] [--big-mb 200]
  python3 tidy.py apply plan.json [--only sort,duplicates,installers,...]
  python3 tidy.py undo  FOLDER/_tidy/undo-<timestamp>.json

Standard library only; works on macOS, Windows and Linux.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

KINDS = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".heic", ".webp", ".tif", ".tiff", ".bmp", ".svg", ".raw", ".cr2", ".nef", ".arw", ".dng"},
    "Videos": {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"},
    "Audio": {".mp3", ".m4a", ".wav", ".aac", ".flac", ".aiff"},
    "Documents": {".pdf", ".doc", ".docx", ".pages", ".txt", ".rtf", ".md", ".odt"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".numbers", ".ods"},
    "Presentations": {".ppt", ".pptx", ".key", ".odp"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".tgz"},
    "Design": {".psd", ".ai", ".sketch", ".fig", ".xd", ".indd", ".afdesign", ".afphoto", ".eps"},
    "Code": {".js", ".ts", ".py", ".json", ".html", ".css", ".sh", ".rb", ".yml", ".yaml"},
}
INSTALLERS = {".dmg", ".pkg", ".exe", ".msi", ".appimage", ".deb", ".rpm"}
JUNK_NAMES = {".ds_store", "thumbs.db", "desktop.ini"}
KEEP_NAMES = {".localized"}  # macOS uses it to name the folder; leave it
PARTIALS = {".crdownload", ".part", ".download", ".tmp"}
SCREENSHOT_PREFIXES = ("screenshot", "screen shot", "cleanshot", "capture")
SKIP_DIRS = {"_tidy", "_to_delete", ".git", "node_modules", ".Trash"}
SORTED_DIRS = set(KINDS) | {"Installers", "Screenshots", "Other"}
# --to-home: where each kind lands in the home folder. Kinds not listed keep
# their own name as a new folder in ~/ (~/Design, ~/Archives, ~/Other, ...).
HOME_FOLDERS = {
    "Images": "Pictures",
    "Videos": "Movies",
    "Audio": "Music",
    "Documents": "Documents",
    "Spreadsheets": "Documents",
    "Presentations": "Documents",
    "Screenshots": "Screenshots",
}


def tidy_dir(root, to_home):
    """Where the plan and undo logs live. With --to-home they go in a hidden
    ~/.tidy/<folder> so the folder being emptied isn't left with a _tidy folder."""
    if to_home:
        return Path.home() / ".tidy" / Path(root).name
    return Path(root) / "_tidy"


def rel_or_abs(path, root):
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def kind_of(path):
    ext = path.suffix.lower()
    if ext in INSTALLERS:
        return "Installers"
    if path.name.lower().startswith(SCREENSHOT_PREFIXES):
        return "Screenshots"
    for kind, exts in KINDS.items():
        if ext in exts:
            return kind
    return "Other"


def file_hash(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def walk(root, top_only):
    """Files under root, skipping our own folders and app bundles."""
    if top_only:
        for entry in os.scandir(root):
            if entry.is_file(follow_symlinks=False):
                yield Path(entry.path)
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith((".app", ".photoslibrary", ".bundle"))]
        for name in filenames:
            yield Path(dirpath) / name


def scan(root, old_days, big_mb, top_only, deep_duplicates=False, to_home=False):
    root = root.resolve()
    home = Path.home().resolve()
    if to_home and root == home:
        sys.exit("--to-home sorts a folder into your home folder; it can't sort the home folder itself")
    trash = (home / "_to_delete") if to_home else Path("_to_delete")
    now = time.time()
    files = []
    for p in walk(root, top_only):
        try:
            st = p.stat()
        except OSError:
            continue
        files.append({"path": str(p.relative_to(root)), "size": st.st_size, "mtime": st.st_mtime})

    by_size = {}
    for f in files:
        if f["size"] > 0:
            by_size.setdefault(f["size"], []).append(f)
    dup_groups = []
    for same in by_size.values():
        if len(same) < 2:
            continue
        by_hash = {}
        for f in same:
            try:
                by_hash.setdefault(file_hash(root / f["path"]), []).append(f)
            except OSError:
                continue
        for group in by_hash.values():
            if len(group) > 1:
                # Keep the oldest copy with the shortest name ("photo.jpg" over "photo (1).jpg").
                group.sort(key=lambda f: (f["mtime"], len(f["path"])))
                dup_groups.append({"keep": group[0]["path"], "extra": [g["path"] for g in group[1:]], "size": group[0]["size"]})

    dup_extra = {p for g in dup_groups for p in g["extra"]}
    actions = []
    for f in files:
        rel = Path(f["path"])
        name = rel.name.lower()
        age_days = (now - f["mtime"]) / 86400
        reason = None
        nested = len(rel.parts) > 1
        if name in KEEP_NAMES:
            continue
        # A copy inside a folder is usually part of a kit (fonts, a site, an
        # export) that breaks if pieces are pulled out, so only loose copies
        # are flagged unless asked.
        if (f["path"] in dup_extra) and (deep_duplicates or not nested):
            reason = "duplicates"
        elif name in JUNK_NAMES or rel.suffix.lower() in PARTIALS or f["size"] == 0:
            reason = "junk"
        elif rel.suffix.lower() in INSTALLERS and age_days > 14:
            reason = "installers"
        if reason:
            actions.append({"from": f["path"], "to": str(trash / reason / rel), "group": reason, "size": f["size"]})
            continue
        # Sort only loose files at the top level; existing subfolders are the person's own system.
        if len(rel.parts) == 1:
            kind = kind_of(rel)
            year = datetime.fromtimestamp(f["mtime"]).strftime("%Y")
            if to_home:
                # Into the person's own folders; only screenshots get year folders,
                # so ~/Documents doesn't fill up with 2023/ 2024/ folders.
                dest = home / HOME_FOLDERS.get(kind, kind)
                if kind == "Screenshots":
                    dest = dest / year
            else:
                dest = Path(kind)
                if kind in ("Screenshots",) or age_days > old_days:
                    dest = dest / year
            actions.append({"from": f["path"], "to": str(dest / rel.name), "group": "sort", "size": f["size"]})

    big = sorted((f for f in files if f["size"] >= big_mb * 1024 * 1024), key=lambda f: -f["size"])[:25]
    old = [f for f in files if (now - f["mtime"]) / 86400 > old_days]
    totals = {}
    for a in actions:
        t = totals.setdefault(a["group"], {"files": 0, "bytes": 0})
        t["files"] += 1
        t["bytes"] += a["size"]

    return {
        "root": str(root),
        "to_home": to_home,
        "scanned_at": datetime.now().isoformat(timespec="seconds"),
        "file_count": len(files),
        "total_bytes": sum(f["size"] for f in files),
        "summary": {g: {**t, "human": human(t["bytes"])} for g, t in totals.items()},
        "duplicates": dup_groups,
        "largest": [{"path": f["path"], "size": human(f["size"])} for f in big],
        "old_files": len(old),
        "actions": actions,
    }


def unique(dest):
    if not dest.exists():
        return dest
    stem, suffix, i = dest.stem, dest.suffix, 2
    while True:
        candidate = dest.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def apply(plan_path, only):
    plan = json.loads(Path(plan_path).read_text())
    root = Path(plan["root"])
    log_dir = tidy_dir(root, plan.get("to_home", False))
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"undo-{stamp}.json"
    moved, skipped = [], 0
    for a in plan["actions"]:
        if only and a["group"] not in only:
            continue
        src = root / a["from"]
        if not src.exists():
            skipped += 1
            continue
        dest = unique(root / a["to"])  # an absolute "to" (--to-home) replaces root
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moved.append({"from": str(src.relative_to(root)), "to": rel_or_abs(dest, root)})
        # Written as we go, so an interrupted run can still be undone.
        log_path.write_text(json.dumps({"root": str(root), "moves": moved}, indent=1))
    print(json.dumps({"moved": len(moved), "skipped_missing": skipped, "undo_log": str(log_path) if moved else None}))


def undo(log_path):
    log = json.loads(Path(log_path).read_text())
    root = Path(log["root"])
    restored = 0
    for m in reversed(log["moves"]):
        src, dest = root / m["to"], root / m["from"]
        if src.exists() and not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            restored += 1
    Path(log_path).rename(Path(log_path).with_suffix(".undone.json"))
    print(json.dumps({"restored": restored, "of": len(log["moves"])}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("folder")
    s.add_argument("--out")
    s.add_argument("--old-days", type=int, default=180)
    s.add_argument("--big-mb", type=int, default=200)
    s.add_argument("--top-only", action="store_true", help="only look at files directly in the folder")
    s.add_argument("--deep-duplicates", action="store_true", help="also flag duplicate copies inside subfolders")
    s.add_argument("--to-home", action="store_true", help="sort into the home folder (~/Pictures, ~/Documents, ...) instead of folders inside FOLDER")
    a = sub.add_parser("apply")
    a.add_argument("plan")
    a.add_argument("--only", help="comma list of groups: sort,duplicates,junk,installers")
    u = sub.add_parser("undo")
    u.add_argument("log")
    args = ap.parse_args()

    if args.cmd == "scan":
        folder = Path(args.folder).expanduser()
        if not folder.is_dir():
            sys.exit(f"Not a folder: {folder}")
        plan = scan(folder, args.old_days, args.big_mb, args.top_only, args.deep_duplicates, args.to_home)
        out = Path(args.out) if args.out else tidy_dir(folder.resolve(), args.to_home) / "plan.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(plan, indent=1))
        report = {k: v for k, v in plan.items() if k not in ("actions", "duplicates")}
        report["duplicate_groups"] = len(plan["duplicates"])
        report["total"] = human(plan["total_bytes"])
        report["plan"] = str(out)
        print(json.dumps(report, indent=1))
    elif args.cmd == "apply":
        apply(args.plan, set(args.only.split(",")) if args.only else None)
    else:
        undo(args.log)


if __name__ == "__main__":
    main()
