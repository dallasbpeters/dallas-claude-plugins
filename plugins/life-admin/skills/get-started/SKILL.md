---
name: get-started
description: First-time setup for the life-admin plugin. Asks a few questions, connects email, calendar and folders, optionally creates a notes vault, sets up a morning inbox sweep, and runs a first cleanup. Use when someone says "set me up", "get started", "I just installed life-admin", "help me set this up", or "what can this do".
---

# Get started

Set up life-admin for someone who may not be technical. Keep every message short and plain: no file paths, no jargon, one step at a time. Ask, do the step, confirm it worked, move on.

Open with one reassuring line: nothing gets sent, deleted or unsubscribed without their yes.

## 1. Ask (one question at a time, or AskUserQuestion with all four)

1. **Email:** Gmail, Outlook, iCloud, Proton, or something else? More than one?
2. **Computer:** Mac or Windows?
3. **Biggest headache right now:** email, messy files, keeping track of tasks, or all of it?
4. **Notes:** do they use a notes app (Apple Notes, Obsidian, Notion, none)?

## 2. Connect

- **Email and calendar:** check which connectors are already connected. For one that's missing, search the connector registry and offer it (Gmail and Google Calendar, or Outlook and Microsoft calendar). The person approves the sign-in themselves.
  - Proton: point them to the proton-mail plugin from the same marketplace, and its setup steps.
  - iCloud Mail or other: say no direct connector is available yet; life-admin still helps with files, notes and tasks.
- **Folders:** ask them to connect Downloads and Desktop (and Documents if they want) so file cleanup can see them. On the desktop app, request folder access; otherwise explain the "Add folder" button.

## 3. Notes (only if they want a place for notes and tasks)

Offer a simple notes folder (second-brain skill). If they use Obsidian on a phone too, put the vault in iCloud Drive → Obsidian (Mac/iPhone) so it syncs. Create the folder layout and a `60 Tasks.md`. Skip this entirely if they'd rather not.

## 4. First wins (pick based on their headache)

- **Email:** run inbox-zero on the last 30 days first, so it's quick and they see results. Show before/after counts.
- **Files:** run a file-cleanup scan on Downloads, show the summary, apply only what they approve.
- **Tasks:** ask what's on their mind and capture it as a task list.

## 5. Keep it going

Offer, one at a time:
- A **morning inbox sweep** as a scheduled task (weekday mornings, drafts only, never sends). Use the scheduling tools available; call it a "scheduled task".
- A **Sunday weekly reset** as a scheduled task.

## 6. Leave them with three phrases

End with what they can say any time:
- "Clean up my email"
- "Clean up my Downloads"
- "Weekly reset"

## Rules

- Never ask for passwords, codes or account numbers in chat. Sign-ins happen in the app's own sign-in windows.
- Nothing is sent, deleted or unsubscribed without a clear yes.
- Their email, files and notes are theirs: don't copy them anywhere else.
