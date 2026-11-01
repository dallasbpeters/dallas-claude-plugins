---
name: second-brain
description: Keeps a person's scattered work, thoughts, people and history in one place, Almanac Desk (or a plain-markdown folder when Almanac Desk isn't installed), by capturing notes and tasks, filing them, pulling in material from email, documents and past chats, and answering "what do I know about X". Use when someone says "save this to my notes", "capture this", "add a task", "file my notes", "set up my second brain", "what do I know about <client/person/project>", "pull this into my notes", or "organize my notes".
---

# Second brain

One place holds notes, people, projects and tasks. **Almanac Desk** is that place when it's installed; otherwise a plain folder of markdown files is.

## 1. Find the home

- **Almanac Desk** is installed when `~/.almanac-desk/assistant/memory` exists (request access to `~/.almanac-desk` if needed). Use it, and read `~/.almanac-desk/assistant/AGENTS.md` first: it is the source of truth for Almanac's conventions and changes with app updates. Then follow **Almanac Desk** below.
- **No Almanac Desk:** use the markdown folder the person names (an Obsidian vault, a Documents folder) and follow **Markdown folder** below. If they have neither, offer to set up the markdown folder.

A person's personal setup (such as a personal plugin) can name a different home; that wins.

## 2. Almanac Desk

Everything is plain Markdown under `~/.almanac-desk/assistant/memory/`, shown in Almanac's notes panel.

| What | Where |
|---|---|
| Quick capture, the day's notes | today's daily note, `memory/YYYY-MM-DD.md` |
| Project, client, person or reference note | `memory/notes/<short-name>.md`, first line `# Title` |
| Meeting | `memory/meetings/` (Almanac records these itself) |
| Tasks | Almanac's **My Tasks**, only through the `almanac-tasks` CLI |

**Grouping.** The sidebar's groups, favorites and icons live in `memory/.sidebar.json`. Grouping never moves files: to file a note, add its path (relative to `memory/`) to that group's `notes` list, and create the group if it doesn't exist. Keep daily notes where they are.

**Tasks.** Run `~/.almanac-desk/bin/almanac-tasks` (never edit `tasks.json` by hand):
- capture now, sort later: `almanac-tasks add "Title" --inbox`
- a real task: `almanac-tasks add "Title" --due <date> --notes "..." [--requester NAME] [--quadrant 1-4]`
- something someone owes: `almanac-tasks add "Title" --waiting-on NAME --due <follow-up day>`
- done: `almanac-tasks done <id|text>`; list: `almanac-tasks list`
In a note, mention a task as `[[task:<id>]]` so it shows as a live checkbox.

**Blocks.** The notes panel renders plain Markdown blocks: callouts (`> [!note]`, `> [!important]`, `> [!warning]`), questions for the person (`> [!question] Title` with the options as bullets; they answer in the panel), and collapsed context (`> [!toggle]- Title`). Put long source material (an email thread, a transcript) inside a toggle.

## 3. Markdown folder

```
00 Inbox/    quick captures
10 Projects/ one note per project
20 Areas/    ongoing responsibilities
30 People/   one note per person or client
40 Notes/    ideas and references
50 Journal/  daily notes, YYYY-MM-DD.md
60 Tasks.md  the one task list: - [ ] task 📅 YYYY-MM-DD #project
90 Archive/
Templates/
```

Create only what's missing; never rename or move the person's own folders. Note templates are in `references/templates.md`.

## 4. The work, either way

- **Capture:** write it down as given, with a `source:` line (chat, email from X, a call), into today's daily note or the inbox. Turn anything with a verb and a deadline into a task.
- **File:** move or merge each captured note into its project, client or person note under a dated heading, and link the people and projects it mentions (`[[Name]]`), creating notes that are missing. Report what went where. Never delete a note; a merged original goes to the archive (markdown) or stays where it is and is left out of the groups (Almanac).
- **Pull things in:** for a client or project, search the source (email, documents, calendar, past chats), then write or update its note: a short summary at the top, then a dated log of decisions, prices, deadlines and contacts, each linking back to its source. Confirm the list of subjects before a big import, and go one subject at a time.
- **Answer from it:** for "what do I know about X" or "where was I on Y", search the notes first (filenames, then full text), read the matching ones, and answer with links to them. Say plainly when the notes don't cover something.

## Rules

- Plain Markdown only. Edit in place; never rewrite a whole note from memory or drop text the person wrote.
- Don't store passwords, account numbers or ID numbers in notes; leave a pointer ("in 1Password") instead.
- Keep work notes and personal notes apart (different groups or folders). Never copy an employer's confidential details into a personal or client note.
