# Dallas's Claude plugins

Plugins that help Claude with personal admin. Nothing here sends email, deletes files, or changes anything without asking.

| Plugin | For | What it does |
|---|---|---|
| **life-admin** | anyone | Inbox zero, safe file cleanup, a markdown second brain (works with Obsidian), a weekly reset, and a guided "set me up". |
| **proton-mail** | Proton Mail users on a Mac | Lets Claude work in a Proton inbox through Proton Mail Bridge. Drafts only; never sends or permanently deletes. |
| **dallas-os** | Dallas only | Points the above at Dallas's vault, mail, dallaspeters.com and Stripe. |

**New here? Start with [SETUP.md](SETUP.md).**

## Install

**Claude app:** where you manage plugins, add a marketplace from GitHub and enter `dallasbpeters/dallas-claude-plugins`, then install the plugins you want.

**Claude Code:**
```
/plugin marketplace add dallasbpeters/dallas-claude-plugins
/plugin install life-admin@dallas-claude-plugins
```

## What's in here

```
.claude-plugin/marketplace.json   the list of plugins
plugins/
  life-admin/
    skills/                        get-started, inbox-zero, file-cleanup, second-brain, weekly-reset
    skills/file-cleanup/scripts/   tidy.py (scan, apply, undo) and its tests
    evals/                         behaviour checks, run with scripts/eval.sh
  proton-mail/
    server/server.mjs              the connector, bundled (no npm install needed)
    src/                           its source; rebuild with scripts/build.sh
    skills/proton-mail/            setup and troubleshooting
    evals/
  dallas-os/
    skills/my-setup/               where Dallas's things live
    evals/
scripts/
  test.sh                          free checks: manifests, file-cleanup tests, connector starts
  eval.sh                          runs the eval suites (small cost per run)
  build.sh                         rebuilds the Proton bundle and makes .plugin files in dist/
SETUP.md                           plain-language setup for a new person
```

## Working on it
- Before pushing: `scripts/test.sh`. After changing a skill: `scripts/eval.sh <plugin>`.
- Add a plugin: create `plugins/<name>/` with `.claude-plugin/plugin.json` and `skills/<skill>/SKILL.md`, add it to `.claude-plugin/marketplace.json`, add a few `evals/<case>/prompt.md` + `graders/criteria.md`, bump versions, push.
- People who installed from this marketplace get changes when they update the plugin.

## Secrets
None live here. The Proton password stays in the Mac Keychain; the dallaspeters.com connector key lives in Vercel and in Claude's connector settings only.
