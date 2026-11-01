---
name: second-brain
description: Keeps a person's scattered work, thoughts, people and history in one plain-markdown notes folder (an Obsidian vault) by capturing notes, filing the inbox, pulling in material from email, documents and past chats, and answering "what do I know about X". Use when someone says "save this to my notes", "capture this", "file my notes inbox", "set up my second brain", "what do I know about <client/person/project>", "pull this into my vault", or "organize my notes".
---

# Second brain

One folder of markdown files is the single place things live. Obsidian (or any markdown app) reads it; Claude reads and writes it directly through the connected folder. Nothing here needs a special app or account.

## The layout

Create only what's missing; never rename or move the person's existing folders without asking.

```
00 Inbox/        quick captures, unsorted
10 Projects/     things with an end: one note per project ("Viaskai launch.md")
20 Areas/        ongoing responsibilities: Home, Money, Health, Kids, Business
30 People/       one note per person or client
40 Notes/        ideas, references, how-tos, things learned
50 Journal/      daily notes, YYYY-MM-DD.md
60 Tasks.md      the one task list
90 Archive/      finished projects and old material
Templates/
```

See `references/templates.md` for the note templates and frontmatter.

## Capture

- Write to `00 Inbox/` as `YYYY-MM-DD <short title>.md`, with the text as given plus a `source:` line (chat, email from X, voice memo).
- Tasks go to `60 Tasks.md` as `- [ ] task 📅 YYYY-MM-DD #project` (date optional).

## File the inbox

For each inbox note: decide where it belongs, move it there (or merge it into an existing note under a dated heading), and add `[[links]]` to the people and projects it mentions, creating those notes if missing. Report what went where. Never delete a note; a merged note's original moves to `90 Archive/merged/`.

## Pull things in

When asked to bring in history from email, documents, calendar or past chats:
1. Search the source for the subject (a client, a project, a person).
2. Write or update the matching Project / Person note: a short summary at the top, then a dated log of what happened (decisions, prices, deadlines, contacts) with a link back to the source where there is one.
3. Keep facts the person said or that the source shows; mark guesses as guesses.
Go one subject at a time, and confirm the list of subjects before a big import.

## Answer from it

For "what do I know about X" or "where was I on Y", search the folder first (filenames, then full text), read the matching notes, and answer with links to them. Say plainly when the notes don't cover something.

## Rules

- Plain markdown, `[[wikilinks]]`, YAML frontmatter. No proprietary formats.
- Edit in place; never rewrite a whole note from memory, and never drop text the person wrote.
- Don't store passwords, account numbers or ID numbers in notes; leave a pointer ("in 1Password") instead.
- Sensitive notes (health, legal, money) stay where the person puts them and are never quoted into other notes.
