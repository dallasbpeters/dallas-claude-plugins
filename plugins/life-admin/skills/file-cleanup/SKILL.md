---
name: file-cleanup
description: Cleans up a messy folder (Downloads, Desktop, Documents, a project folder) safely by sorting loose files by type, pulling out duplicates, old installers and junk, and never deleting anything. Use when someone says "clean up my Downloads", "my desktop is a mess", "find duplicate files", "what's taking up space", "organize this folder", or "undo the cleanup".
---

# File cleanup

Tidy a folder in three steps: **look, agree, move**. Nothing is ever deleted. Files are moved into sorted folders or into a `_to_delete` folder the person empties themselves, and every run can be undone.

**Downloads and Desktop are emptied into the home folder, not sorted in place.** For those two, always scan with `--to-home`: loose files go to the person's own top-level folders instead of new folders inside Downloads or Desktop.

| Kind | Goes to |
|---|---|
| Images | `~/Pictures` |
| Videos | `~/Movies` |
| Audio | `~/Music` |
| Documents, spreadsheets, presentations | `~/Documents` |
| Screenshots | `~/Screenshots/<year>` |
| Design, Archives, Code, Installers, Other | a folder of that name in `~/` (`~/Design`, …) |

With `--to-home`, files land loose in those folders (no year folders except screenshots), `_to_delete` is `~/_to_delete`, and the plan and undo logs live in `~/.tidy/<folder name>/`, so nothing is left behind in Downloads or Desktop. Subfolders the person made inside Downloads or Desktop stay where they are. For any other folder (a project, Documents), sort in place as before unless they ask otherwise.

The work is done by `${CLAUDE_PLUGIN_ROOT}/skills/file-cleanup/scripts/tidy.py` (Python 3, standard library only; macOS, Windows, Linux). Run it in a shell that can see the folder: the person's connected folder on their computer. If no folder is connected, ask them to connect the one they want cleaned (Downloads or Desktop is the usual start).

## 1. Look

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-cleanup/scripts/tidy.py" scan ~/Downloads --to-home
python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-cleanup/scripts/tidy.py" scan "<other folder>"
```

Options: `--top-only` (just the loose files, not subfolders; good for Desktop), `--deep-duplicates` (also flag copies inside subfolders; off by default because pulling files out of a font kit or site export breaks it), `--old-days 180`, `--big-mb 200`.

The scan writes the full plan to `<folder>/_tidy/plan.json` (with `--to-home`: `~/.tidy/<folder name>/plan.json`) and prints a summary; its `plan` field is the path. Report it in plain words, for example:

- 412 loose files would move to ~/Pictures, ~/Documents, ~/Screenshots (by year), ~/Installers… (or, in place: Images, Documents, …)
- 38 duplicate copies (2.1 GB) would go to `_to_delete/duplicates`; the oldest copy is kept
- 12 old installers (.dmg/.exe older than two weeks) → `_to_delete/installers`
- 9 junk files (.DS_Store, empty files, half-finished downloads) → `_to_delete/junk`
- The 5 biggest files, so they can decide about those themselves

Read `plan.json` to answer questions ("which duplicates?", "where would X go?").

## 2. Agree

Ask which groups to apply: `sort`, `duplicates`, `junk`, `installers`. Default to all only when they've said "just do it". Subfolders the person already made are never rearranged; only loose top-level files are sorted. If they want a different layout (by project, by client, by month), edit the `to` paths in `plan.json` before applying.

## 3. Move

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-cleanup/scripts/tidy.py" apply "<plan path from the scan>" --only sort,duplicates,junk,installers
```

Then tell them:
- how many files moved, and where they went
- that `_to_delete` (`~/_to_delete` for Downloads/Desktop) is theirs to review and empty (drag to Trash / Recycle Bin)
- that it can be undone

## Undo

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/file-cleanup/scripts/tidy.py" undo "<folder>/_tidy/undo-<timestamp>.json"   # or ~/.tidy/<folder name>/undo-<timestamp>.json
```

## Rules

- Never delete, empty the Trash, or overwrite. Moving into `_to_delete` is as far as it goes. A name clash gets " (2)" added, which matters more with `--to-home` because ~/Pictures and ~/Documents already hold files.
- Never run `--to-home` on the home folder itself (the script refuses).
- Don't touch app bundles, photo libraries, `.git` or `node_modules` (the script skips them).
- Scan a big folder (home, Documents) only when asked, and say it may take a few minutes.
- For files on cloud drives (iCloud, Dropbox, OneDrive) that may not be downloaded, mention that scanning reads them and may download them.
