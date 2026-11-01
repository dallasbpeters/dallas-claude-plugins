# Life admin

Five helpers for keeping personal admin under control in Claude:

| Ask Claude… | What happens |
|---|---|
| "Clean up my email" | Groups mail by sender, archives the noise in bulk, stars what needs you, drafts easy replies, suggests unsubscribes. **Never sends or permanently deletes.** |
| "Clean up my Downloads" | Scans the folder, shows a plan (sort by type, duplicates, old installers, junk), and moves only what you approve. **Never deletes:** extras go to a `_to_delete` folder you empty yourself, and every run can be undone. |
| "Save this to my notes" / "What do I know about X?" | Keeps notes, people, projects and tasks in Almanac Desk when it's installed, or in one folder of markdown notes (works with Obsidian). |
| "Money review" / "What am I paying for?" | Reads your bank data (via a finance connector such as the cashflow plugin, which uses Plaid) and billing email, then gives a short snapshot, past-due and failed payments first, every subscription in one list, and a ranked list of what to cancel, fix or pay. **Never moves money or cancels anything:** it proposes, and drafts the emails. |
| "Weekly reset" | Email, calendar, tasks, notes and files in one sweep, ending with your top 3 for the week. |

## Setup
1. Install this plugin.
2. Connect your email (Gmail or Outlook) and calendar under Connectors. For money reviews, also install the cashflow plugin and link your banks.
3. Connect the folders you want help with (Downloads, Desktop, and a notes folder, such as an Obsidian vault) from the desktop app.
4. Try: "Clean up my email" or "Clean up my Downloads".

The file cleanup needs Python 3 (already on macOS; on Windows, install it from python.org or the Microsoft Store).
