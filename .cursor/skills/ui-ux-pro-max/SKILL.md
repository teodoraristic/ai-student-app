---
name: ui-ux-pro-max
description: >-
  UI/UX design intelligence for web and mobile. Covers styles, color palettes,
  font pairings, product patterns, UX guidelines, and chart choices across
  React, Next.js, Vue, Svelte, SwiftUI, React Native, Flutter, Tailwind,
  shadcn/ui, and HTML/CSS. Use when planning, building, designing, reviewing,
  fixing, improving, or refactoring UI for websites, landing pages, dashboards,
  admin panels, e-commerce, SaaS, portfolios, blogs, or mobile apps—especially
  for components (buttons, modals, navbars, sidebars, cards, tables, forms,
  charts), color systems, accessibility, animation, layout, typography,
  spacing, interaction states, shadows, and gradients. When shadcn/ui MCP is
  available, use it for component search and examples.
---

# UI/UX Pro Max

Design and UX workflow backed by a small searchable dataset (`data/*.csv`) and extended rules in [reference.md](reference.md). Run the search script from the **repository root** (paths below assume this skill lives in `.cursor/skills/ui-ux-pro-max/`).

## When to apply

**Must use** when work changes how something looks, feels, moves, or is interacted with: new pages, components, themes, responsive behavior, motion, navigation, forms, charts, or UI review for accessibility and consistency.

**Recommended** when polish is unclear, pre-launch UI passes, or cross-platform (web / iOS / Android) alignment.

**Skip** for pure backend, APIs-only, non-UI automation, or performance work with no UI surface.

**Decision rule:** If the task affects visual or interaction design, use this skill.

## Priority order (what to fix first)

1. Accessibility → 2. Touch and interaction → 3. Performance (UI-related) → 4. Style consistency → 5. Layout and responsive → 6. Typography and color → 7. Animation → 8. Forms and feedback → 9. Navigation → 10. Charts and data.

Full table and checklists: [reference.md](reference.md).

## Workflow

### Step 1 — Parse the request

Extract: product type and industry, audience, tone keywords (minimal, playful, dense, etc.), primary **stack** (infer from repo: `package.json`, framework imports, mobile config), and deliverable (page, component, review).

### Step 2 — Design system (required before large UI builds)

Run `--design-system` first for synthesized recommendations:

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<product> <industry> <keywords>" --design-system -p "Project Name"
```

Markdown output:

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system -f markdown -p "Project Name"
```

**Persist** master + optional page override (creates `design-system/` in the **current working directory**):

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name"
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system --persist -p "Project Name" --page "dashboard"
```

Hierarchy: `design-system/pages/<page>.md` overrides `design-system/MASTER.md` when both exist.

### Step 3 — Domain deep dives

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<keywords>" --domain <domain> [-n 12]
```

Domains: `product`, `style`, `color`, `typography`, `landing`, `chart`, `ux`, `google-fonts`, `react`, `web`, `prompt`.

### Step 4 — Stack-specific notes

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "<keywords>" --stack <stack> [-n 12]
```

Stacks: `react`, `nextjs`, `vue`, `svelte`, `swiftui`, `react-native`, `flutter`, `tailwind`, `shadcn`, `html-css`.

Aliases: `next` → `nextjs`, `rn` → `react-native`, `html` → `html-css`.

## Integrations

- **shadcn/ui MCP:** When available, search and cite official patterns instead of inventing markup.
- **Dataset expansion:** Add rows to `data/*.csv`; rerun searches. Script uses keyword scoring—no migration step.

## Prerequisites

Python 3.10+ recommended. From repo root, `python` / `python3` should resolve.

## Output expectations for the agent

After `--design-system`, implement using the returned palette, type, layout, and anti-pattern list. Cross-check critical items in [reference.md](reference.md) (contrast, focus, touch targets, motion reduction).

## Additional resources

- Hub + priority table + dataset notes: [reference.md](reference.md)
- Full quick reference, professional UI tables, delivery checklists: [reference-checklists.md](reference-checklists.md)
- Copy-paste scenarios: [examples.md](examples.md)

## Maintenance

- Keep `SKILL.md` under 500 lines; add long lists to `reference.md`.
- Third-person description; trigger terms live in `description` for discovery.
