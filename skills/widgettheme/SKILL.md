---
name: widgettheme
description: Apply "The Morning Paper" — the user's personal light newspaper/editorial design system (cream paper backgrounds, ink-black text, deep newspaper-red accent #8b1a1a, Georgia serif type, thin hairline rules) taken from their productivity-widget and productivity-diary apps. Use this skill whenever the user says "widget theme", "follow the widget theme", "match the widget theme", "use my theme", "make it look like my widget/diary", "morning paper theme", or invokes /widgettheme — for ANY UI, web page, app, dashboard, poster, or artifact that should match their signature look. Also trigger when the user asks to restyle or theme something to be consistent with their personal productivity widget/diary even if they never say the word "widget".
---

# The Morning Paper — the widget theme

This is the user's personal design language: a warm, light **newspaper / editorial** aesthetic. It comes from their own apps (`productivity-widget` = a Tkinter desktop widget; `productivity-diary` = a deployed web app), so applying it keeps their projects visually consistent.

When the user says "widget theme" / "follow the widget theme" / "match my widget", apply the tokens and motifs below. Do not invent a different palette.

## Design tokens (authoritative)

Use these exact values. Drop-in stylesheet is bundled at `assets/theme.css` — copy its `:root` block into the target project's CSS.

```css
:root{
  /* Surfaces */
  --color-paper:#faf8f3;   /* main paper / card background */
  --color-outer:#f0ede6;   /* page / panel background behind cards */
  --color-white:#ffffff;   /* elevated surface */

  /* Ink */
  --color-ink:#1a1a1a;         /* primary text */
  --color-ink-light:#4a4a4a;   /* secondary text */
  --color-muted:#6b6b6b;       /* muted / captions */

  /* Accent — newspaper red */
  --color-accent:#8b1a1a;
  --color-accent-dark:#6b1212; /* hover / pressed */

  /* Rules & borders */
  --color-border:#d4cfc7;
  --color-border-light:#e8e4dc;

  /* Semantic */
  --color-productive:#1a7f37;  /* good / green */
  --color-distracting:#b3261e; /* bad / red */
  --color-neutral:#b8860b;     /* gold (ratings, stars) */

  /* Type — system fonts only, no web fonts */
  --font-heading:Georgia,'Times New Roman',serif;
  --font-body:Georgia,'Times New Roman',serif;
  --font-sans:'Segoe UI',Arial,sans-serif;   /* small labels / eyebrows */
  --font-mono:'Courier New',Courier,monospace; /* data, timers, numerals */

  /* Spacing */
  --spacing-xs:4px; --spacing-sm:8px; --spacing-md:16px;
  --spacing-lg:24px; --spacing-xl:32px; --spacing-xxl:48px;

  /* Shape & elevation */
  --radius-card:4px;
  --shadow-card:0 2px 8px rgba(0,0,0,0.08);
}
```

## Signature motifs (this is what makes it read as "the theme")

- **Masthead**: uppercase, `letter-spacing: 0.14em`, accent red `#8b1a1a`, often the user's name/title.
- **Red rules**: a `3px solid var(--color-accent)` rule under the masthead; `3px double` ink rules (`#1a1a1a`) under major section headings; thin `1px` hairlines (`--color-border-light`) as dividers.
- **Serif display**: use Georgia for headings, body, and large numerals. It should feel like a well-set print page, not a SaaS dashboard.
- **Sans for tiny labels only**: `'Segoe UI'` for eyebrow/kicker labels and meta text.
- **Mono for data**: `'Courier New'` for anything numeric/tabular/timestamp-like.
- **Cards**: paper surface on the outer background, `1px` border, `4px` radius, the soft card shadow.
- **No gradients.** The theme is flat, warm, and restrained. (The indigo→violet gradient found in the widget's icon script is NOT part of the theme.)

## How to apply (checklist)

1. Set the page background to `--color-outer`, cards/content surfaces to `--color-paper`.
2. Set body text to `--color-ink`; secondary text `--color-ink-light`; captions `--color-muted`.
3. Use `--color-accent` for links, active states, emphasis, and rules — sparingly (it is a strong red).
4. Switch headings/body to Georgia; use Segoe UI for small uppercase labels; Courier New for numbers.
5. Add the rule motifs (red under masthead, double ink under sections, hairlines between blocks).
6. Cards get the `4px` radius + soft shadow + hairline border.
7. Keep it light by default. If a dark mode is needed, use the **Night Edition** below.

## Night Edition (optional dark variant)

Keep the identity (serif, red accent, rules) but invert surfaces:

```css
[data-theme="night"]{
  --color-paper:#1c1a17; --color-outer:#141210;
  --color-ink:#f0ede6; --color-ink-light:#c9c4ba; --color-muted:#8a857c;
  --color-border:#3a3630; --color-border-light:#2a2722;
  --color-accent:#d64545; --color-accent-dark:#b3261e;
  --shadow-card:0 2px 8px rgba(0,0,0,0.4);
}
```

## Guardrails

- **System fonts only.** Do not add Google Fonts or any external font/CDN — the theme must work offline.
- **Don't substitute a different palette.** If the target already has a theme, the user is explicitly asking to override it.
- **Keep accessibility**: maintain strong contrast (ink on paper), visible focus states, and semantic HTML.
- Minor known discrepancy: border is `#d4cfc7` (used by the app + email templates). Ignore the stray `#d4cfc4` if seen.

## Source of truth (for traceability)

- Palette and fonts come from the author's Morning Paper apps ([juw12/morning-paper-web](https://github.com/juw12/morning-paper-web)): the widget's `THEME` dict and the web version's `:root` CSS tokens. `assets/theme.css` in this skill is the portable copy.
