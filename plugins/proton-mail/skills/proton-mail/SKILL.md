---
name: proton-mail
description: Sets up and uses the Proton Mail connector (Proton Mail Bridge on a Mac), and troubleshoots it when its tools fail. Use when someone says "connect my Proton mail", "set up Proton", "Proton isn't working", "Bridge login failed", or asks to search, clean up, label or draft in a Proton inbox.
---

# Proton Mail

The connector talks to **Proton Mail Bridge**, which runs on the person's Mac and serves their decrypted mail locally over IMAP (127.0.0.1, port 1143). It can list folders, summarize senders, search, read, move (archive, spam, trash), label, flag, create folders, unsubscribe, and save drafts. It **cannot send or permanently delete**, by design.

For cleaning an inbox, follow the life-admin `inbox-zero` skill if it's installed; the tools here are how it reaches Proton.

## First-time setup (walk the person through it)

1. **Install and sign in to Proton Mail Bridge** (proton.me/mail/bridge). It needs a paid Proton plan.
2. In Bridge, click the account and note the **IMAP username** and **password** Bridge shows. That password is Bridge's own, not their Proton password.
3. **Save the Bridge password to the Keychain**, so it never sits in a file. Have them run this in Terminal, with their Bridge username; it asks for the password without showing it:
   ```bash
   security add-generic-password -a "BRIDGE_USERNAME" -s proton-bridge -w
   ```
4. Make sure Node.js is installed (`node -v` in Terminal; if missing, install it from nodejs.org).
5. Quit and reopen Claude, then try `list_folders`.

The connector reads the username from that Keychain item, so no other settings are needed. Optional environment overrides: `PROTON_BRIDGE_USER`, `PROTON_FROM` (the From line on drafts), `PROTON_BRIDGE_IMAP_PORT`, `PROTON_BRIDGE_PASSWORD`.

Never ask for the Bridge password in chat. If the person shares it anyway: don't repeat it back, don't write it into any file, config or environment variable, and don't offer to; tell them to type it at the Keychain prompt themselves, and suggest regenerating it in Bridge afterwards since it was shared in chat.

## When it fails

| Error | Fix |
|---|---|
| Connection refused / timed out | Bridge isn't running, or the Mac is asleep. Open Bridge. |
| "Bridge refused the login" | The Keychain item has the wrong password (often their Proton password instead of Bridge's). Re-run step 3 after deleting the old item in Keychain Access (search "proton-bridge"). |
| "No Bridge password found" / "No Bridge username" | Step 3 wasn't done, or was done under a different service name. |
| Tools missing entirely | Node isn't installed or Claude wasn't restarted. |
| A long move stops partway | Calls time out after about a minute; work in batches (`max` 600 on `move_matching`, or narrower date ranges) and keep going. |

## Working habits

- Search results are sorted newest first; reading a message keeps it unread.
- Archive is a move to "Archive". Trash is a move, never a purge.
- Drafts land in Proton's Drafts folder; the person sends them from Proton.
- `unsubscribe` uses the sender's one-click header when there is one, a mailto (saved as a draft), or returns the link for the person to open. Only unsubscribe from senders the person approved.
