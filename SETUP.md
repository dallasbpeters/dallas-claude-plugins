# Setting up life-admin

About 15 minutes. You need the Claude desktop app and a paid Claude plan.

## 1. Install
1. Open the Claude desktop app.
2. Where you manage plugins, add a marketplace from GitHub: `dallasbpeters/dallas-claude-plugins`
3. Install **life-admin**. If you use Proton Mail, also install **proton-mail**.

## 2. Let Claude set the rest up
Start a new chat and type:

> set me up

Claude will ask which email you use, what kind of computer you have, and what's bugging you most. Then it walks you through connecting your email and calendar and giving it your Downloads and Desktop folders, and does a first cleanup with you.

## What it will and won't do
- **Email:** archives the junk, stars what needs you, writes reply drafts. It **never sends** anything and never permanently deletes. Drafts wait in your Drafts folder for you.
- **Files:** sorts your Downloads and Desktop and finds duplicates and old installers. It **never deletes**: extras go into a `_to_delete` folder you empty yourself, and every cleanup can be undone.
- **Unsubscribing:** only from senders you say yes to.

## Things to say any time
- "Clean up my email"
- "What needs a reply?"
- "Clean up my Downloads"
- "Save this to my notes: …"
- "Weekly reset"
- "Undo the file cleanup"

## If something isn't working
Tell Claude what happened, for example "my email isn't connecting". The usual fix is reconnecting the email connector, or reopening the Claude app.
