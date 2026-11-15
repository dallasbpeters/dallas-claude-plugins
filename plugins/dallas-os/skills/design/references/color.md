# Color

- Write every theme color in OKLCH.
- Keep all colors in one central theme file, so brand colors, logos, and marks change in one place.
- Use only colors from the theme, at their base step unless you mean a different step. Use the tokens directly, never hard-coded values.
- When users can change a background, set the text color with `contrast-color()` or similar, not a fixed color.
- Never use a red primary for positive or confirming actions. Red reads as negative.
- Put grouped sections on a neutral step token, not a custom background. (Sections need a calm surface that matches the rest of the design system.)
- Use the chart palette's third color for positive values. (Positive values should read the same way everywhere.)
- Give related chart data the same color across every chart. (Matching colors help readers link related data.)
- Use the sequential scale for ordered values and the diverging scale for values that split around a midpoint.
- Rotate the diverging scale's hue to color groups of chart elements. (Gives each group a distinct color from one scale.)
