---
name: claude-files
description: Decides where Claude saves files on the person's computer (one home folder, never the Desktop or Downloads) and sweeps up Claude's leftovers into an archive. Use whenever Claude is about to write a file, export, image, download or scratch folder onto the person's computer, and when someone says "Claude leaves files everywhere", "clean up Claude's files", "where did you save that", or "run the Claude sweep".
---

# Claude's files

Everything Claude makes on this computer lives in **one home folder**, so nothing piles up on the Desktop, in Downloads, or as stray folders next to the person's own work.

## The home folder

- Default: `~/Documents/Claude`. If the person's setup names a different one (for example in a personal plugin), use that.
- Layout: `<home>/<YYYY-MM>/<short-project-name>/`, for example `~/Documents/Claude/2026-11/bird-creek-ads/`.
- Create the month and project folders as needed. Use short, lowercase, dashed project names.

## Where to save, in order

1. **The person named a place** ("put it in the Bird Creek folder"): save it there.
2. **The file belongs to a project folder or repo you are already working in** (code, a plugin, an asset that project uses): save it inside that project, where the project expects it.
3. **Everything else** (exports, drafts, images, reports, scratch work, downloaded files): save it in the home folder layout above.

Never:
- create new folders at the top of the Desktop, Downloads, Documents or a projects folder
- name things "Claude outputs", "untitled" or "test" outside the home folder
- leave scratch or intermediate files behind. Put them in `<home>/<YYYY-MM>/<project>/scratch/` or in the session's own scratch space.

After saving, say where in plain words ("saved to Claude → November → bird-creek-ads").

## The sweep

`${CLAUDE_PLUGIN_ROOT}/skills/claude-files/scripts/sweep.py` finds Claude's leftovers and moves them to `<home>/Archive/<YYYY-MM>/`, keeping a readable trail of where each came from. Nothing is ever deleted, and every run can be undone.

It looks for:
- "Claude outputs"-style folders
- loose `claude-*` files at the top of a folder that are older than two weeks
- `.plugin` packages outside a repo's `dist/` folder
- old `_tidy` cleanup plans
- git leftovers Claude couldn't delete (`.git/stale-*lock*`, `.git/push-*.bundle`, `tmp_obj_*`)

1. **Scan.** Pass the home folder, then the connected folders to look through:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/claude-files/scripts/sweep.py" scan ~/Documents/Claude ~/Desktop ~/Downloads ~/Development
   ```
   Report what it found by reason, with sizes, in plain words.
2. **Agree.** Apply only with a yes, unless this is the scheduled monthly sweep the person set up to run on its own.
3. **Apply:** `... sweep.py apply ~/Documents/Claude/sweep-plan.json`
4. **Undo if needed:** `... sweep.py undo <home>/Archive/<YYYY-MM>/undo-<stamp>.json`

Skip anything inside a folder the person is actively using for something else, and anything that looks like their own work rather than Claude's. When unsure, list it instead of moving it.
