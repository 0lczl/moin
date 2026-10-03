# Moin Design Guide

Updated 2026-09-23. This is the current visual identity for مُعين / Moin,
our Arabic religious translation machine and its future website. Product
priorities live in [.specs/model-selection.md](.specs/model-selection.md).

## Source of truth

The chosen identity comes from [the official presentation](presentation/مُعين-التقديم الرسمي-الحكام.pptx).
The reusable assets are in [brand/presentation/](brand/presentation/README.md).
The current Studio implements this identity in `base-station/moin_studio/static/`.

## Logo

Use [moin-logo.svg](brand/presentation/moin-logo.svg), extracted from slide 1.
It preserves the presentation's gold symbol and Arabic wordmark; only the slide
background and separator lines were removed when preparing the asset.

- Use the complete supplied artwork with its original proportions and colors.
- Place the gold logo on a solid deep-green surface, as in the presentation.
- Preserve clear space around it; do not stretch, rotate, redraw, or add effects.
- Do not substitute typed artwork for the supplied logo.
- For linked logos, use an accessible name such as `مُعين — Moin`; decorative
  repetitions should have empty alt text.
- On tiny displays, use a readable text label if the full logo becomes illegible;
  a separate small-format mark would need an explicit design decision.

## Colors

| Role | Value | Application |
| --- | --- | --- |
| Deep green | `#16311F` | Brand panels, navigation, primary actions |
| Gold | `#E1BF75` | Original logo, accents on green |
| Ivory | `#F5F3EE` | Main background, text on green |
| Ink | `#1B2A20` | Body text on light surfaces |
| Muted green | `#5D6B62` | Secondary text on light surfaces |
| Bronze | `#C0912D` | Focus rings and accent rules |
| Dark gold | `#8A6516` | Small accent text on ivory |
| Warm surface | `#EFEBE1` | Secondary panels |
| Warm border | `#D9C9A4` | Dividers and quiet outlines |
| Pale green | `#A9BCAE` | Secondary text on deep green |

```css
:root {
  --moin-green: #16311f;
  --moin-gold: #e1bf75;
  --moin-bg: #f5f3ee;
  --moin-ink: #1b2a20;
  --moin-muted: #5d6b62;
  --moin-bronze: #c0912d;
  --moin-dark-gold: #8a6516;
  --moin-surface: #efebe1;
  --moin-border: #d9c9a4;
  --moin-on-dark-muted: #a9bcae;
}
```

Use dark text on light surfaces. Light gold is primarily decorative or used on
green, not for small body text on ivory. Confirm contrast for the actual text
size and state before shipping. Error and warning colors are functional colors,
not additional brand colors; always pair status color with readable text.
Studio currently uses `#A6382C` for errors.

## Typography

- **Arabic:** IBM Plex Sans Arabic, supplied locally in weights 400/500/600/700.
- **Latin:** Arimo, as used in the presentation. Studio currently uses it when
  installed and falls back to the bundled IBM Plex Sans Arabic. Arimo is not
  bundled yet; package an appropriately licensed font before requiring identical
  Latin typography across devices.
- Load [fonts.css](brand/presentation/fonts.css) from the same origin. Do not
  depend on a font CDN for local operation.

```html
<link rel="stylesheet" href="/brand/presentation/fonts.css">
```

```css
body { font-family: 'Arimo', 'IBM Plex Sans Arabic', sans-serif; }
:lang(ar), [dir='rtl'] { font-family: 'IBM Plex Sans Arabic', sans-serif; }
```

Use 400 for body text, 500/600 for hierarchy, and 700 for strong emphasis.
For web layouts, start with 15–17px body text and 21–23px Arabic transcription;
allow generous Arabic line height (around 1.9–2). Responsive titles may range
from 32–58px. These are Studio starting points, not rigid presentation sizes.
Do not apply Latin uppercase or tracking rules to Arabic. Set direction per
text block, and isolate filenames, timestamps, and URLs within RTL content.

## Layout and interaction

Use calm ivory workspaces, deep-green brand regions, restrained gold accents,
and clear typographic hierarchy. The current Studio uses straight dividers and
small corner radii (roughly 3–5px for controls), rather than pill-shaped panels
or gold glow effects. Keep logo panels rectangular and the artwork unrotated.

Prioritize the user's task: supply media, see processing status, read Arabic
and translations, and play audio. Benchmark screens should make source audio,
candidate output, and review decisions easy to compare. Dense result tables
need readable spacing; they should not inherit oversized presentation layouts.

Use short, restrained color/opacity transitions. Respect reduced-motion
preferences, provide visible keyboard focus, and keep controls usable by touch.
Uncertainty, failed processing, and withheld translations must remain explicit.
Visual polish is not evidence of translation accuracy.

## Applying the identity later

- **Website:** reuse these assets and tokens when exposing the machine through
  a public interface. Choosing a frontend stack is separate from choosing models.
- **Presentations:** retain the chosen deck's artwork, palette, and typography.
  Only make performance claims supported by completed evaluations.
- **Devices:** preserve legibility and concise language names; font availability
  and display resolution determine implementation. Hardware work is future scope.
## Remaining decisions

Before a public website, verify font redistribution terms, bundle the chosen
Latin font if needed, and check contrast, keyboard use, RTL layout, and mobile
readability on the implemented pages. This guide records the chosen identity;
it does not claim those future acceptance checks have already passed.
