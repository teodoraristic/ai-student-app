# UI/UX Pro Max — Reference Hub

This file orients the agent. **Executable searches** use `scripts/search.py` and `data/*.csv` (extend rows anytime). **Normative guidance** lives in [reference-checklists.md](reference-checklists.md).

## Rule categories by priority

| Priority | Category | Impact | Domain | Key checks (must have) | Anti-patterns (avoid) |
|----------|----------|--------|--------|------------------------|------------------------|
| 1 | Accessibility | CRITICAL | `ux` | Contrast 4.5:1, alt text, keyboard nav, aria-labels | Removing focus rings, icon-only buttons without labels |
| 2 | Touch and interaction | CRITICAL | `ux` | Min size 44×44px, 8px+ spacing, loading feedback | Hover-only, instant 0ms state changes |
| 3 | Performance | HIGH | `ux` | WebP/AVIF, lazy loading, reserve space (CLS < 0.1) | Layout thrashing, cumulative layout shift |
| 4 | Style selection | HIGH | `style`, `product` | Match product type, consistency, SVG icons | Mixing flat and skeuomorphic randomly, emoji as icons |
| 5 | Layout and responsive | HIGH | `ux` | Mobile-first breakpoints, viewport meta, no horizontal scroll | Fixed px containers, disable zoom |
| 6 | Typography and color | MEDIUM | `typography`, `color` | Base 16px, line-height 1.5, semantic tokens | Body < 12px, gray-on-gray, raw hex in components |
| 7 | Animation | MEDIUM | `ux` | 150–300ms, meaningful motion, spatial continuity | Decorative-only, animating width/height, no reduced-motion |
| 8 | Forms and feedback | MEDIUM | `ux` | Visible labels, errors near fields, helper text | Placeholder-only label, errors only at top |
| 9 | Navigation patterns | HIGH | `ux` | Predictable back, bottom nav ≤5, deep linking | Overloaded nav, broken back, no deep links |
| 10 | Charts and data | LOW | `chart` | Legends, tooltips, accessible colors | Color alone for meaning |

## Domains and stacks (search)

**Domains:** `product`, `style`, `color`, `typography`, `landing`, `chart`, `ux`, `google-fonts`, `react`, `web`, `prompt`

**Stacks:** `react`, `nextjs`, `vue`, `svelte`, `swiftui`, `react-native`, `flutter`, `tailwind`, `shadcn`, `html-css`

## Dataset scale note

The bundled CSVs are **starter seeds**. The skill description advertises large counts (palettes, pairings, etc.); grow `data/*.csv` to reach that depth—`search.py` does not hard-code limits beyond `-n`.

## Prerequisites (Python)

```bash
python3 --version || python --version
```

Install if missing: macOS `brew install python3`; Debian/Ubuntu `sudo apt update && sudo apt install python3`; Windows `winget install Python.Python.3.12`.

## Query strategy

- Combine **product + industry + tone + density** in one query string.
- Always run `--design-system` before large UI builds, then `--domain` / `--stack` refinements.
- For shadcn projects, prefer MCP component discovery over guessing Radix markup.

## Pre-read for audits

Before shipping UI, scan [reference-checklists.md](reference-checklists.md) sections **1–3** (accessibility, touch, performance) and run:

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "animation accessibility z-index loading" --domain ux -n 12
```

## Related files

- [reference-checklists.md](reference-checklists.md) — full quick reference, professional UI tables, delivery checklists
- [examples.md](examples.md) — command sequences
