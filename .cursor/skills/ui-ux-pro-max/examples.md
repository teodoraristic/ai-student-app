# UI/UX Pro Max — Examples

Run commands from the **repository root**. Adjust the relative path if the skill is installed under `~/.cursor/skills/ui-ux-pro-max/`.

## New SaaS dashboard

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "b2b saas analytics dense modern" --design-system -p "Northwind"
python .cursor/skills/ui-ux-pro-max/scripts/search.py "data table keyboard" --domain ux -n 8
python .cursor/skills/ui-ux-pro-max/scripts/search.py "virtual list rerender" --stack react -n 8
```

## Landing page refresh

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "ai devtool minimal dark" --design-system -f markdown -p "Codegen"
python .cursor/skills/ui-ux-pro-max/scripts/search.py "hero social proof" --domain landing
python .cursor/skills/ui-ux-pro-max/scripts/search.py "glassmorphism" --domain prompt
```

## Persisted design system + page override

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "fintech crypto trust" --design-system --persist -p "Ledgerly" --page "dashboard"
```

Then ask the agent:

> I am building the Dashboard page. Read `design-system/MASTER.md` and `design-system/pages/dashboard.md` if present; page rules override master. Generate the UI accordingly.

## Accessibility pass before ship

Skim [reference.md](reference.md) sections 1–3, then run:

```bash
python .cursor/skills/ui-ux-pro-max/scripts/search.py "focus keyboard contrast motion" --domain ux -n 12
```
