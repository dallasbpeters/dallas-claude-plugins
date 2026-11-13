# Process and code

- Implement from the referenced design file (Paper) and match the prototype exactly. Check it before you build.
- Prototype in code with real demo apps, not in Figma. Design new screens on the fly in a branch.
- Sketch ideas in a design canvas (Paper) before or alongside code.
- Present AI-built prototypes as direction, not final design or final code. Set stakeholder expectations.
- Use the existing design system component first (accordion, form, modal, button, text field, layout). Override it lightly before you write custom CSS.
- Style with the project's design system classes and naming (for example Optics BEM). No one-off classes.
- Write styles as named BEM classes, with modifiers nested under their block. Do not stack utility classes in markup.
- Write CSS with native nesting, no `:is()`, one stylesheet per component, and tokens only. No inline styles.
- Consolidate CSS. No new stylesheet per feature. Merge duplicate rules. Do not invent extra classes or leave code comments. Run a make-it-right pass to cut code you do not need.
- Make a change on the default variant when you can, not across many call sites. Prefer CSS-only changes.
- When you port a prototype to production, drop its variable and class names. Use only design system classes and tokens.
- Change only what was asked. Never restyle neighboring components. Do not commit UI changes until Dallas has reviewed them.
- Test every layout at mobile and tablet widths before you call it done.
- Make editable site content (banners, CTAs, colors, messages) controllable in the CMS, not hard-coded.
- Keep a site map of every view and a checklist of what is not done yet (brand, leave-behinds, export).
- Write PR descriptions as a short summary of the change's theme. No code and no test details.
