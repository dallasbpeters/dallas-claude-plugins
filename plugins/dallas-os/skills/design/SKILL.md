---
name: design
description: Dallas's design rules and taste, learned from his own Claude sessions. Use for any design or front-end work - building or styling a page, screen, or component, CSS, layout, color, type, icons, charts and dashboards, UI copy, brand and marketing sites, motion and video, accessibility, and turning a prototype into production code. Also use when Dallas says "make it look right", "match the design", "fix the styling", or reviews a UI.
user-invocable: true
argument-hint: "[review · color|type|layout|components|icons|charts|ux|copy|brand|motion|a11y|process · rules · add] [target]"
---

# Dallas's design rules

These are decisions Dallas made in past sessions. Follow them unless he says otherwise in the session. When a rule and a project's own design system disagree, the design system wins, and you say so.

## Commands

`/design <command> [target]`. The target is a file, component, route, or URL. With no target, use the work in this session.

| Command | Aliases | What it does | Reads |
| --- | --- | --- | --- |
| `review` | `audit`, `check` | Check the target against every rule. | all files |
| `color` | `colors` | Apply or check the color rules. | [color](references/color.md) |
| `type` | `typography`, `fonts` | Apply or check the type rules. | [typography](references/typography.md) |
| `layout` | `spacing`, `grid` | Apply or check spacing and layout. | [spacing-layout](references/spacing-layout.md) |
| `components` | `component`, `ui` | Apply or check component rules. | [components](references/components.md) |
| `icons` | `images`, `imagery`, `logos` | Apply or check icons, images, and logos. | [icons-imagery](references/icons-imagery.md) |
| `charts` | `data`, `dashboard` | Apply or check charts and data views. | [charts-data](references/charts-data.md) |
| `ux` | `patterns`, `flow` | Apply or check UX patterns. | [ux-patterns](references/ux-patterns.md) |
| `copy` | `words`, `labels` | Apply or check UI copy. | [ui-copy](references/ui-copy.md) |
| `brand` | `marketing`, `site` | Apply or check brand rules. | [brand](references/brand.md) |
| `motion` | `animation`, `video` | Apply or check motion rules. | [motion](references/motion.md) |
| `a11y` | `accessibility` | Apply or check accessibility. | [accessibility](references/accessibility.md) |
| `process` | `build`, `css` | How Dallas wants design work done and coded. | [process](references/process.md) |
| `rules` | `list` | Show the rules, or one category's rules (`/design rules icons`). | the named file |
| `add` | `remember` | Save a new rule: `/design add icons: Use 1.5px strokes`. | none |

## How to run

1. **No argument:** show the commands table in short form and ask which one. Do not start work.
2. **A category command:** read [process](references/process.md) and the category file.
   - **With a target:** check the target against each rule. List what breaks a rule, as `rule → where → fix`. Then fix it, changing only what the rules cover. Do not restyle anything else.
   - **No target:** apply the rules to the design work in this session, and say which rules you applied.
3. **`review`:** read every reference file. Check the target and group what you find by category, worst first. Ask before a large fix. Make small fixes at once.
4. **`rules`:** print the rules as they are in the file. Do not summarize them.
5. **`add`:** add one line to the end of `~/.almanac-desk/assistant/memory/notes/design-rules-inbox.md`, under a `## <today> · <project folder>` heading. Use the format `- [x] **<slug>:** <rule> (<why>)`. The slug is one of: process-tools, color, typography, spacing-layout, components, icons-imagery, charts-data, ux-patterns, ui-copy, brand, motion, accessibility. Write the rule as one short command sentence. Tell Dallas it goes into the skill tonight.
6. **Unknown command:** if a word matches a category or alias, use it. If not, treat the whole argument as the target of `review`.

When this skill loads without a command, because the work is design work, read [process](references/process.md) and the category files that match the task. Check the work against them before you say it is done.

## How the rules grow

A Claude Code hook reads Dallas's sessions and finds new design decisions. They wait in his Almanac Desk inbox (`memory/notes/design-rules-inbox.md`). Each night, the rules he kept are added here by category, and the plugin is committed and pushed. Do not edit the reference files by hand during a session. Use `/design add`.
