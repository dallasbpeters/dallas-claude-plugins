---
name: my-setup
description: Dallas's personal setup, which tells the life-admin skills where his things live: Almanac Desk (all notes and tasks), Proton Mail and Gmail, the dallaspeters.com site connector, Stripe, and his projects folder. Use whenever Dallas asks about his notes, vault, tasks, clients, proposals, invoices, agreements, payments, email, files, or says "weekly reset", "file my inbox", "what do I know about…", "catch me up".
---

# Where Dallas's things live

## Notes and tasks: Almanac Desk
Almanac Desk is the one home for Dallas's notes and tasks, work and personal. It replaces the Obsidian vault; don't write to Obsidian. Where this differs from the life-admin `second-brain` skill's folder layout, Almanac's conventions win.

- **Folder:** `~/.almanac-desk/assistant/memory` (request access to `~/.almanac-desk` if it isn't connected). Read `~/.almanac-desk/assistant/AGENTS.md` before writing; it is the source of truth for the conventions below and Almanac Desk updates it.
- **Daily notes:** `memory/YYYY-MM-DD.md`. Quick captures for a day go in that day's note.
- **Standalone notes** (projects, clients, people, write-ups): `memory/notes/<short-name>.md`, starting with a `# Title` line. Meetings: `memory/meetings/`. Weekly 15Five: `memory/15five/`.
- **Sidebar groups** live in `memory/.sidebar.json`. Grouping never moves files: to file a note, add its path (relative to `memory/`) to the group's `notes` list. Existing groups include Almanac, BetaNXT, Marketing, 1-on-1 and Boundaryless; add one per freelance client (Viaskai, TSRP, Bird Creek, Unruly Chain) the first time it's needed. `assistant/scripts/sort-notes.py` files ungrouped notes by rules.
- **Tasks:** the Almanac Desk **My Tasks** list, only through the `almanac-tasks` CLI at `~/.almanac-desk/bin/almanac-tasks` (never edit `tasks.json` by hand). Use `--inbox` for quick captures, `--requester` for things someone asked for, `--waiting-on` for things owed to him, and `--quadrant`. In notes, reference a task as `[[task:<id>]]`.
- **Notes panel blocks** are plain Markdown: callouts (`> [!note]`, `> [!important]`), questions for Dallas as `> [!question]` callouts with options as bullets, and long context inside `> [!toggle]-`.
- **Rituals** are Almanac's own skills (`/plan-day`, `/almanac-daily-review`, weekly planning, `/fifteen-five`). For a "weekly reset", run life-admin's `weekly-reset`, but take the tasks from `almanac-tasks list` and save the plan into the day's note.
- **Work vs. personal:** both live here now. RoleModel work stays in its groups; client and personal notes get their own groups. Never put RoleModel-confidential details into a freelance client note, or into a site brand kit.
- **Into brand kits:** when Dallas asks to pull a client's history into its brand kit references on the site, read the client's Almanac notes and meetings, and use the note path as each reference's source.

## Business: dallaspeters.com
- **Photos connector** (custom connector in Claude): `site_overview`, `list_proposals`, `get_proposal`, `get_agreement`, `list_invoices`, `draft_invoice`, `list_reviews`, `recent_activity`, `search_photos`.
- If those tools are missing, it isn't connected yet. Setup, once:
  1. Terminal: `openssl rand -hex 32`, then copy the result.
  2. Vercel → photo-portfolio → Settings → Environment Variables: add `MCP_ACCESS_TOKEN` (Production) with that value, then redeploy.
  3. Claude → Settings → Connectors → Add custom connector: name "Photos", URL `https://www.dallaspeters.com/api/mcp/<token>`.
  The URL contains the key: never paste it into notes, email or the repo. To revoke it, change the env var and redeploy.
- Invoices from Claude are **drafts**; Dallas sends them from Admin → Invoices. Sending agreements, countersigning and deleting stay in the admin.
- Code: `~/Development/addison-photos`.

## Payments: Stripe
- Stripe is connected as a Claude connector. Use it to read customers, invoices, payments and balances, for example "who still owes me?" or "what came in this month?".
- Create or send invoices through the site (above), not directly in Stripe, so they stay tied to proposals and agreements. Never refund, cancel or change anything in Stripe without an explicit yes for that specific item.

## Email
- **Proton** (dallas@dallaspeters.com) through the proton-mail plugin or connector; Bridge must be running. **Gmail** through the Gmail connector.
- The **morning inbox sweep** is already a scheduled task; don't create another.
- Drafts only. Never send, never permanently delete, unsubscribe only with a yes.

## Keeping notes current
When something changes on a client (proposal accepted, agreement signed, invoice paid, an important email), add a dated line to that client's note in `memory/notes/`, and add or close the matching task with `almanac-tasks`.

## Weekly reset additions
Also run `site_overview` and `recent_activity`. Under "Waiting on", list unpaid invoices (site + Stripe) and unsigned agreements.

## Where Claude saves files
- Home folder: `~/Documents/Claude` (iCloud-backed), laid out as `<YYYY-MM>/<project>/`. The life-admin `claude-files` skill has the rules; follow it for every file Claude writes on this Mac.
- Exceptions: code and plugin files go in their repo under `~/Development/<repo>`; Framer components go in the connected framer-components project folder.
- Never write to the Desktop, Downloads or `~/Claude` (that one belongs to the Claude app).
- A monthly Claude sweep runs as a scheduled task; don't create another.

## Files
- Projects: `~/Development`. Cleanup candidates: Downloads, Desktop, `~/Screenshots`. Use life-admin `file-cleanup`.
