---
name: my-setup
description: Dallas's personal setup, which tells the life-admin skills where his things live: the Obsidian vault in iCloud, Almanac Desk work notes, Proton Mail and Gmail, the dallaspeters.com site connector, Stripe, and his projects folder. Use whenever Dallas asks about his notes, vault, tasks, clients, proposals, invoices, agreements, payments, email, files, or says "weekly reset", "file my inbox", "what do I know about…", "catch me up".
---

# Where Dallas's things live

## Notes
- **Personal vault:** iCloud Drive → Obsidian → `Vault` (syncs to his iPhone). On the Mac: `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault`. Request access to `~/Library/Mobile Documents` if it isn't connected. Layout and rules: life-admin `second-brain`. Start page `Home.md`, tasks `60 Tasks.md`, clients in `30 People/`.
- iCloud can briefly lock files mid-sync ("Resource deadlock avoided"): wait and retry, never force.
- **Work notes (RoleModel):** Almanac Desk, plain markdown in `~/.almanac-desk/assistant/memory` (daily notes, meetings, 15Five). Read them for work questions; don't copy them into the personal vault.

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
When something changes on a client (proposal accepted, agreement signed, invoice paid, an important email), add a dated line to their note in `30 People/` and the project in `10 Projects/`.

## Weekly reset additions
Also run `site_overview` and `recent_activity`. Under "Waiting on", list unpaid invoices (site + Stripe) and unsigned agreements.

## Where Claude saves files
- Home folder: `~/Documents/Claude` (iCloud-backed), laid out as `<YYYY-MM>/<project>/`. The life-admin `claude-files` skill has the rules; follow it for every file Claude writes on this Mac.
- Exceptions: code and plugin files go in their repo under `~/Development/<repo>`; Framer components go in the connected framer-components project folder.
- Never write to the Desktop, Downloads or `~/Claude` (that one belongs to the Claude app).
- A monthly Claude sweep runs as a scheduled task; don't create another.

## Files
- Projects: `~/Development`. Cleanup candidates: Downloads, Desktop, `~/Screenshots`. Use life-admin `file-cleanup`.
