---
name: system-monitor
description: Checks why Dallas's Mac is slow and cleans up what AI coding sessions leave behind, which means runaway or forgotten processes (dev servers, MCP servers, headless browsers, agent CLIs), Claude artifacts or previews still running, and git worktrees nobody is using. Use when Dallas says "my machine is slow", "check my system resources", "what's running", "what's eating memory", "kill leftover processes", "clean up worktrees", "clean up after Claude", or "system cleanup".
---

# System monitor and cleanup

Three steps: **look, agree, act**. The scan changes nothing. Nothing is stopped or removed until Dallas says which things.

The work is done by `${CLAUDE_PLUGIN_ROOT}/skills/system-monitor/scripts/sysmon.py` (Python 3, standard library only).

## Where it has to run

On the Mac itself, in a real shell (Claude Code in a terminal, or a desktop session whose Bash runs on the Mac). A cloud session or the Cowork VM sees its own processes and its own paths, not the Mac's, so:

- Don't run `scan` there and report it as the Mac. Don't run `git worktree prune` or `remove` there either: every worktree looks missing from inside the VM, and pruning would wipe the records of live ones. `apply` refuses when the host or home folder differs from the scan.
- From such a session, give Dallas this one line to paste into Terminal, then read `~/.sysmon/plan.json` through the connected home folder:
  `python3 ~/Development/dallas-claude-plugins/plugins/dallas-os/skills/system-monitor/scripts/sysmon.py scan`
- Activity Monitor through computer use only gives the totals (memory used, swap, load). Its process list doesn't refresh in the background, so don't rely on it for per-process numbers.

## 1. Look

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/system-monitor/scripts/sysmon.py" scan
```

Options: `--roots DIR ...` (default `~/Development ~/Code ~/intent/workspaces ~/conductor ~/ShipStudio`), `--stale-days 14`.

It writes everything to `~/.sysmon/plan.json` and prints a summary. Report it in plain words, worst first:

- **The machine:** memory used and swap, load against the number of cores, disk free, how long since the last restart. Swap above a few GB or weeks of uptime is worth saying out loud; a restart is often the quickest fix.
- **What's heavy right now:** the top few processes by CPU and the top few apps by memory (helpers are added up under their app).
- **Leftover dev processes:** dev servers, MCP servers, headless browsers and agent CLIs, with what started each one, how long it has run, its port and its folder. `suggest_stop` marks the ones whose parent is gone and that have run over 12 hours, or whose folder no longer exists.
- **Claude artifacts and previews:** check the artifact list on the device and any preview or dev server Claude started (they show up in the dev process list by port). Say which are still running.
- **Worktrees**, by verdict:
  - `prune`: the folder is already gone and only git's record is left (most `/tmp` and `/private/tmp/claude-…/scratchpad` worktrees after a restart)
  - `remove`: clean, pushed or merged, untouched for 14+ days, nothing running in it
  - `review`: has uncommitted changes or commits that exist only on this Mac
  - `keep`: touched recently or something is running in it
- **Scratch folders:** sizes of `/private/tmp/claude*`, `~/intent/workspaces/*` and `~/conductor/workspaces/*`.

Read `plan.json` to answer questions ("which worktrees?", "what's on port 3000?").

## 2. Agree

Ask which of these to do, and list the actual items for each:

- `prune`: always safe, it only clears records of folders that are gone.
- `worktrees`: every worktree marked `remove`, or the ones he names. Show path, branch, size and idle days.
- `processes`: only the pids he picks. Show the command, age, memory and port for each. Never offer to stop an app he has open, a database, Proton Mail Bridge, Proton Drive, or anything that belongs to the current Claude session.

`review` worktrees are his call one by one: commit and push, or leave them. Don't remove them.

## 3. Act

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/system-monitor/scripts/sysmon.py" apply ~/.sysmon/plan.json --only prune,worktrees
python3 "${CLAUDE_PLUGIN_ROOT}/skills/system-monitor/scripts/sysmon.py" apply ~/.sysmon/plan.json --only processes --pids 1234,5678
```

`--worktrees PATH,PATH` limits removal to those paths. Then tell him what was stopped, what was removed and how much space came back, and that the log is in `~/.sysmon/apply-<timestamp>.json`.

## What apply does and doesn't do

- Worktrees are removed with `git worktree remove`, never `--force`, so git refuses if anything is uncommitted. The branch stays; the log has the `git worktree add` line that brings each one back.
- Ignored local files such as `.env` are copied to `~/.sysmon/saved/<repo>/<worktree>/` first. `node_modules`, build output and caches are not.
- Processes get a polite stop (SIGTERM), never a forced kill, and only if the pid is still the same command the scan saw.
- It never deletes branches, never touches the main checkout of a repo, and never empties scratch folders. Those stay a manual choice.

## Rules

- Scan first, every time. A plan older than an hour is stale: rescan before acting on it.
- Never stop a process or remove a worktree on a guess. If the scan can't tell what something is, say so and leave it.
- Slow machine with nothing obvious in the scan: say that, and suggest a restart, checking Spotlight and file-sync activity (Proton Drive, Dropbox), and trimming login items, in that order.
