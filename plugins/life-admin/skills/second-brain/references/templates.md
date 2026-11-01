# Note templates

## Project — `10 Projects/<Name>.md`

```markdown
---
type: project
status: active        # active | waiting | done
client: "[[Client Name]]"
started: YYYY-MM-DD
due:
tags: []
---
# <Name>

**What it is:** one or two sentences.
**Next step:** the single next action.

## Log
### YYYY-MM-DD
- What happened, decisions, numbers. (source: email from …)
```

## Person / client — `30 People/<Name>.md`

```markdown
---
type: person          # person | client | company
company:
email:
aliases: []
---
# <Name>

How we know each other, what they care about, how they like to work.

## Log
### YYYY-MM-DD
- …
```

## Area — `20 Areas/<Name>.md`

```markdown
---
type: area
---
# <Name>

Standards to keep, recurring things, links to related projects.
```

## Daily note — `50 Journal/YYYY-MM-DD.md`

```markdown
---
type: daily
---
# <Weekday, Month D>

## Top 3
- [ ]

## Notes

## Done
```

## Tasks — `60 Tasks.md`

```markdown
# Tasks

## Now
- [ ] Task 📅 YYYY-MM-DD #project

## Waiting on
- [ ] Thing — waiting on [[Person]] since YYYY-MM-DD

## Someday
```
