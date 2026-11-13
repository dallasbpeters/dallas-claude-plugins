#!/usr/bin/env python3
"""sysmon: see what is slowing a Mac down and clean up what AI coding sessions leave behind.

  sysmon.py scan  [--roots DIR ...] [--stale-days 14] [--out FILE]
  sysmon.py apply PLAN --only prune,worktrees,processes [--worktrees PATH,...] [--pids N,...]

scan  changes nothing. It writes the full picture to ~/.sysmon/plan.json and prints a summary:
      memory, swap, load, the heaviest processes and apps, leftover dev processes (dev servers,
      MCP servers, headless browsers, agent CLIs) and every git worktree with a verdict.
apply does only what --only names:
      prune      git worktree prune, for worktrees whose folder is already gone
      worktrees  git worktree remove (never --force) for worktrees marked "remove"; the branch
                 is kept, and ignored local files such as .env are copied to ~/.sysmon/saved first
      processes  SIGTERM (never SIGKILL) to the pids given with --pids, and only if each pid is
                 still the same leftover dev process the scan saw

Python 3 standard library only. Must run on the Mac itself: a sandbox or VM sees other
processes and other paths, so apply refuses when the host or home folder differs from the scan.
"""
import argparse, json, os, re, shutil, signal, socket, subprocess, sys, time
from pathlib import Path

HEAVY = {"node_modules", ".next", ".nuxt", ".turbo", ".cache", ".parcel-cache", ".vite", "dist", "build",
         "out", "tmp", "log", "logs", "coverage", ".venv", "venv", "__pycache__", "vendor", ".bundle",
         ".gradle", "Pods", "DerivedData", "target", ".DS_Store", ".sass-cache", "storybook-static"}
DEV = re.compile(
    r"(^|/)(node|bun|deno|tsx|ts-node|nodemon|vite|next|webpack|esbuild|turbo|ruby|puma|rails|foreman|overmind|"
    r"uvicorn|gunicorn|flask|storybook|tailwindcss|ngrok|cloudflared|zrok2?|claude|codex|opencode|gemini|"
    r"playwright|chromium|chrome-headless-shell)(\s|$)"
    r"|--headless|http\.server|manage\.py runserver|[-_/@]mcp([-_/\s.]|$)|npm (run|exec)|npx |pnpm |yarn |bin/dev",
    re.I)


def run(cmd, timeout=20, cwd=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        return r.returncode, r.stdout.strip()
    except Exception:
        return 1, ""


def secs(etime):
    days, _, rest = etime.rpartition("-")
    parts = [int(p) for p in rest.split(":") if p.isdigit()]
    while len(parts) < 3:
        parts.insert(0, 0)
    return int(days or 0) * 86400 + parts[0] * 3600 + parts[1] * 60 + parts[2]


def human_age(s):
    return f"{s // 86400}d {s % 86400 // 3600}h" if s >= 86400 else f"{s // 3600}h {s % 3600 // 60}m"


def system_info():
    info = {"host": socket.gethostname(), "home": str(Path.home()), "platform": sys.platform,
            "cpus": os.cpu_count(), "load": [round(x, 2) for x in os.getloadavg()],
            "uptime": run(["uptime"])[1]}
    du = shutil.disk_usage(str(Path.home()))
    info["disk_free_gb"], info["disk_total_gb"] = round(du.free / 1e9, 1), round(du.total / 1e9, 1)
    if sys.platform == "darwin":
        total = int(run(["sysctl", "-n", "hw.memsize"])[1] or 0)
        vm = run(["vm_stat"])[1]
        page = int((re.search(r"page size of (\d+)", vm) or [0, 4096])[1])
        pages = {k.strip(): int(v) for k, v in re.findall(r"^(.+?):\s+(\d+)\.", vm, re.M)}
        gb = lambda name: round(pages.get(name, 0) * page / 1e9, 1)
        info["memory"] = {"total_gb": round(total / 1e9, 1), "free_gb": gb("Pages free"),
                          "wired_gb": gb("Pages wired down"), "compressed_gb": gb("Pages occupied by compressor"),
                          "swap": run(["sysctl", "-n", "vm.swapusage"])[1],
                          "pressure": run(["memory_pressure", "-Q"])[1].splitlines()[-1:]}
    return info


def app_name(args):
    m = re.search(r"/([^/]+)\.app/", args)
    return m.group(1) if m else os.path.basename(args.split(" ")[0])


def processes():
    _, out = run(["ps", "-axo", "pid=,ppid=,pcpu=,rss=,etime=,user=,args="])
    procs = []
    for line in out.splitlines():
        p = line.split(None, 6)
        if len(p) < 7 or not p[0].isdigit():
            continue
        procs.append({"pid": int(p[0]), "ppid": int(p[1]), "cpu": float(p[2]), "mem_mb": int(p[3]) // 1024,
                      "age_s": secs(p[4]), "user": p[5], "cmd": p[6], "app": app_name(p[6])})
    return [p for p in procs if p["pid"] != os.getpid()]


def lsof_map(args, key):
    """{pid: value-or-list} from lsof -F output ('p<pid>' then 'n<name>' lines)."""
    _, out = run(["lsof"] + args, timeout=30)
    res, pid = {}, None
    for line in out.splitlines():
        if line.startswith("p"):
            pid = int(line[1:])
        elif line.startswith("n") and pid:
            if key == "cwd":
                res[pid] = line[1:]
            else:
                res.setdefault(pid, []).append(line[1:].rsplit(":", 1)[-1])
    return res


def dev_leftovers(procs):
    me = run(["id", "-un"])[1] or os.environ.get("USER", "")
    by_pid = {p["pid"]: p for p in procs}
    dev = [p for p in procs if p["user"] == me and ".app/" not in p["cmd"] and DEV.search(p["cmd"])]
    if not dev:
        return []
    cwds = lsof_map(["-a", "-d", "cwd", "-Fpn", "-p", ",".join(str(p["pid"]) for p in dev)], "cwd")
    ports = lsof_map(["-iTCP", "-sTCP:LISTEN", "-nP", "-Fpn"], "ports")
    rows = []
    for p in dev:
        cwd = cwds.get(p["pid"], "")
        parent = by_pid.get(p["ppid"], {}).get("app", "launchd" if p["ppid"] == 1 else "?")
        flags = []
        if p["ppid"] == 1:
            flags.append("orphan")
        if p["age_s"] > 86400:
            flags.append("old")
        if cwd and not os.path.isdir(cwd):
            flags.append("folder-gone")
        rows.append({"pid": p["pid"], "parent": parent, "age": human_age(p["age_s"]), "age_s": p["age_s"],
                     "cpu": p["cpu"], "mem_mb": p["mem_mb"], "ports": sorted(set(ports.get(p["pid"], []))),
                     "cwd": cwd, "cmd": p["cmd"][:200], "flags": flags,
                     "suggest_stop": "folder-gone" in flags or ("orphan" in flags and p["age_s"] > 43200)})
    return sorted(rows, key=lambda r: (-r["suggest_stop"], -r["mem_mb"]))


def find_repos(roots):
    repos = []
    for root in roots:
        root = os.path.expanduser(root)
        base = root.rstrip("/").count("/")
        for d, dirs, _ in os.walk(root):
            if ".git" in dirs and os.path.isdir(os.path.join(d, ".git")):
                wt = os.path.join(d, ".git", "worktrees")
                if os.path.isdir(wt) and os.listdir(wt):
                    repos.append(d)
                dirs[:] = []
                continue
            dirs[:] = [] if d.count("/") - base >= 4 else [x for x in dirs if x not in HEAVY and x != ".git"]
    return sorted(set(repos))


def git(path, *args, timeout=30):
    return run(["git", "-C", path] + list(args), timeout=timeout)


def local_files(path):
    _, out = git(path, "ls-files", "--others", "--ignored", "--exclude-standard", "--directory")
    return [f for f in out.splitlines() if f.strip("/").split("/")[0] not in HEAVY
            and os.path.basename(f.strip("/")) not in HEAVY][:40]


def worktrees(repos, stale_days, proc_cwds):
    rows, now = [], time.time()
    for repo in repos:
        rc, out = git(repo, "worktree", "list", "--porcelain")
        if rc:
            continue
        default = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")[1]
        if not default:
            default = next((b for b in ("main", "master") if git(repo, "rev-parse", "--verify", "-q", b)[0] == 0), "")
        for block in out.split("\n\n")[1:]:
            f = dict((l.split(" ", 1) + [""])[:2] for l in block.splitlines())
            path = f.get("worktree", "")
            row = {"repo": repo, "path": path, "branch": f.get("branch", "(detached)").replace("refs/heads/", ""),
                   "head": f.get("HEAD", "")[:10]}
            if "prunable" in f or not os.path.isdir(path):
                row.update(verdict="prune", why="folder is gone, only git's record is left")
                rows.append(row)
                continue
            dirty = len(git(path, "status", "--porcelain")[1].splitlines())
            last = int(git(path, "log", "-1", "--format=%ct")[1] or 0)
            for extra in (path, os.path.join(path, ".git")):
                try:
                    last = max(last, int(os.path.getmtime(extra)))
                except OSError:
                    pass
            idle = int((now - last) / 86400)
            unpushed = int(git(path, "rev-list", "--count", "HEAD", "--not", "--remotes")[1] or 0)
            merged = bool(default) and git(repo, "merge-base", "--is-ancestor", f.get("HEAD", "HEAD"), default)[0] == 0
            size = run(["du", "-sk", path], timeout=90)[1].split("\t")[0]
            busy = [pid for pid, c in proc_cwds.items() if c == path or c.startswith(path + "/")]
            row.update(idle_days=idle, changed_files=dirty, unpushed_commits=0 if merged else unpushed,
                       merged=merged, size_mb=int(size) // 1024 if size.isdigit() else None,
                       local_files=local_files(path), busy_pids=busy)
            if busy:
                row.update(verdict="keep", why="a process is running in it")
            elif idle < stale_days:
                row.update(verdict="keep", why=f"touched {idle} days ago")
            elif dirty or row["unpushed_commits"]:
                row.update(verdict="review", why=f"{dirty} changed files, {row['unpushed_commits']} commits only on this Mac")
            else:
                row.update(verdict="remove", why=f"clean, idle {idle} days, " + ("merged" if merged else "pushed"))
            rows.append(row)
    return rows


def scratch():
    rows = []
    for base in ("/private/tmp", os.path.expanduser("~/intent/workspaces"), os.path.expanduser("~/conductor/workspaces")):
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            p = os.path.join(base, name)
            if not os.path.isdir(p) or (base == "/private/tmp" and not name.startswith("claude")):
                continue
            size = run(["du", "-sk", p], timeout=90)[1].split("\t")[0]
            rows.append({"path": p, "size_mb": int(size) // 1024 if size.isdigit() else None,
                         "idle_days": int((time.time() - os.path.getmtime(p)) / 86400)})
    return rows


def scan(args):
    procs = processes()
    apps = {}
    for p in procs:
        a = apps.setdefault(p["app"], {"app": p["app"], "processes": 0, "cpu": 0.0, "mem_mb": 0})
        a["processes"] += 1
        a["cpu"] = round(a["cpu"] + p["cpu"], 1)
        a["mem_mb"] += p["mem_mb"]
    slim = lambda p: {k: (v[:120] if k == "cmd" else v) for k, v in p.items() if k in ("pid", "cpu", "mem_mb", "app", "cmd")}
    dev = dev_leftovers(procs)
    trees = worktrees(find_repos(args.roots), args.stale_days, {d["pid"]: d["cwd"] for d in dev if d["cwd"]})
    for d in dev:
        hit = next((t for t in trees if d["cwd"] and (d["cwd"] == t["path"] or d["cwd"].startswith(t["path"] + "/"))), None)
        if hit:
            d["flags"].append("in-worktree")
    plan = {"scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "system": system_info(), "process_count": len(procs),
            "top_cpu": [slim(p) for p in sorted(procs, key=lambda p: -p["cpu"])[:15]],
            "top_memory": [slim(p) for p in sorted(procs, key=lambda p: -p["mem_mb"])[:15]],
            "top_apps": sorted(apps.values(), key=lambda a: -a["mem_mb"])[:15],
            "dev_processes": dev, "worktrees": trees, "scratch": scratch()}
    out = Path(args.out or Path.home() / ".sysmon" / "plan.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, indent=1))
    count = lambda v: sum(1 for t in trees if t["verdict"] == v)
    mb = lambda v: sum(t.get("size_mb") or 0 for t in trees if t["verdict"] == v)
    print(json.dumps({
        "system": plan["system"], "process_count": len(procs),
        "top_cpu": plan["top_cpu"][:8], "top_apps_by_memory": plan["top_apps"][:8],
        "dev_processes": {"total": len(dev), "suggest_stop": [d for d in dev if d["suggest_stop"]][:20],
                          "memory_mb": sum(d["mem_mb"] for d in dev)},
        "worktrees": {v: {"count": count(v), "size_mb": mb(v)} for v in ("prune", "remove", "review", "keep")},
        "scratch_mb": sum(s["size_mb"] or 0 for s in plan["scratch"]), "plan": str(out)}, indent=1))


def save_local_files(tree):
    dest = Path.home() / ".sysmon" / "saved" / os.path.basename(tree["repo"]) / os.path.basename(tree["path"])
    saved = []
    for rel in tree.get("local_files", []):
        src = Path(tree["path"]) / rel
        if not src.exists():
            continue
        if src.is_dir() and sum(f.stat().st_size for f in src.rglob("*") if f.is_file()) > 5_000_000:
            continue
        target = dest / rel.strip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if src.is_dir() else shutil.copy2)(src, target)
        saved.append(str(target))
    return saved


def apply(args):
    plan = json.loads(Path(args.plan).read_text())
    if plan["system"]["host"] != socket.gethostname() or plan["system"]["home"] != str(Path.home()):
        sys.exit("refusing: this is not the machine (or home folder) the scan ran on. Run apply on the Mac itself.")
    only = set(filter(None, (args.only or "").split(",")))
    if not only:
        sys.exit("nothing to do: pass --only prune,worktrees,processes")
    log = {"applied_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "pruned": [], "removed": [], "skipped": [], "stopped": []}
    if "prune" in only:
        for repo in sorted({t["repo"] for t in plan["worktrees"] if t["verdict"] == "prune"}):
            rc, out = git(repo, "worktree", "prune", "-v")
            log["pruned"].append({"repo": repo, "ok": rc == 0, "output": out})
    if "worktrees" in only:
        chosen = set(filter(None, (args.worktrees or "").split(",")))
        for t in plan["worktrees"]:
            if t["verdict"] == "prune" or (chosen and t["path"] not in chosen) or (not chosen and t["verdict"] != "remove"):
                continue
            if git(t["path"], "status", "--porcelain")[1]:
                log["skipped"].append({"path": t["path"], "why": "has uncommitted changes now"})
                continue
            saved = save_local_files(t)
            rc, out = git(t["repo"], "worktree", "remove", t["path"], timeout=300)
            entry = {"path": t["path"], "branch": t["branch"], "saved_local_files": saved,
                     "undo": f"git -C '{t['repo']}' worktree add '{t['path']}' '{t['branch'] if t['branch'] != '(detached)' else t['head']}'"}
            (log["removed"] if rc == 0 else log["skipped"]).append(entry if rc == 0 else {"path": t["path"], "why": out or "git refused"})
    if "processes" in only:
        known = {d["pid"]: d for d in plan["dev_processes"]}
        for pid in [int(x) for x in (args.pids or "").split(",") if x.strip().isdigit()]:
            now_cmd = run(["ps", "-p", str(pid), "-o", "args="])[1]
            if pid not in known or not now_cmd or now_cmd[:200] != known[pid]["cmd"]:
                log["skipped"].append({"pid": pid, "why": "not a leftover dev process from the scan, or already gone"})
                continue
            os.kill(pid, signal.SIGTERM)
            log["stopped"].append({"pid": pid, "cmd": known[pid]["cmd"]})
    path = Path.home() / ".sysmon" / f"apply-{time.strftime('%Y%m%d-%H%M%S')}.json"
    path.write_text(json.dumps(log, indent=1))
    print(json.dumps({k: len(v) if isinstance(v, list) else v for k, v in log.items()} | {"log": str(path)}, indent=1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--roots", nargs="+", default=["~/Development", "~/Code", "~/intent/workspaces", "~/conductor", "~/ShipStudio"])
    s.add_argument("--stale-days", type=int, default=14)
    s.add_argument("--out")
    a = sub.add_parser("apply")
    a.add_argument("plan")
    a.add_argument("--only", help="comma list: prune,worktrees,processes")
    a.add_argument("--worktrees", help="comma list of worktree paths (default: every worktree marked remove)")
    a.add_argument("--pids", help="comma list of pids to stop (required for processes)")
    args = ap.parse_args()
    scan(args) if args.cmd == "scan" else apply(args)


if __name__ == "__main__":
    main()
