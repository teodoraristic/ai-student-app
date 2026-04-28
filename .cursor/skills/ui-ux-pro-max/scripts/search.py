#!/usr/bin/env python3
"""
UI/UX Pro Max - keyword search over bundled CSV domains.
Run from repo root, e.g.:
  python .cursor/skills/ui-ux-pro-max/scripts/search.py "saas dashboard" --design-system -p "Acme"
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

DOMAIN_FILES = {
    "product": "product.csv",
    "style": "style.csv",
    "color": "color.csv",
    "typography": "typography.csv",
    "landing": "landing.csv",
    "chart": "chart.csv",
    "ux": "ux.csv",
    "google-fonts": "google_fonts.csv",
    "react": "react.csv",
    "web": "web.csv",
    "prompt": "prompt.csv",
}

DESIGN_SYSTEM_DOMAINS = ("product", "style", "color", "typography", "landing")

STACK_FILES = {
    "react": "stack_react.csv",
    "nextjs": "stack_nextjs.csv",
    "vue": "stack_vue.csv",
    "svelte": "stack_svelte.csv",
    "swiftui": "stack_swiftui.csv",
    "react-native": "stack_react_native.csv",
    "flutter": "stack_flutter.csv",
    "tailwind": "stack_tailwind.csv",
    "shadcn": "stack_shadcn.csv",
    "html-css": "stack_html_css.csv",
}

STACK_ALIASES = {
    "next": "nextjs",
    "next.js": "nextjs",
    "rn": "react-native",
    "reactnative": "react-native",
    "html": "html-css",
    "css": "html-css",
}


def tokenize(q: str) -> list[str]:
    q = q.lower()
    return [t for t in re.split(r"[^a-z0-9+#]+", q) if len(t) > 1 or t in {"ai", "ux"}]


def score_row(query_tokens: set[str], row: dict[str, str]) -> float:
    blob = " ".join(row.values()).lower()
    if not blob.strip():
        return 0.0
    score = 0.0
    for t in query_tokens:
        if t in blob:
            score += 3.0 + min(blob.count(t), 5) * 0.5
    # light boost for prefix / substring on longer tokens
    for t in query_tokens:
        if len(t) < 4:
            continue
        if any(w.startswith(t) for w in re.findall(r"[a-z0-9]+", blob)):
            score += 0.5
    return score


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def search_domain(domain: str, query: str, limit: int) -> list[tuple[float, dict[str, str]]]:
    fname = DOMAIN_FILES.get(domain)
    if not fname:
        return []
    rows = read_csv_rows(DATA / fname)
    qtok = set(tokenize(query))
    if not qtok:
        qtok = set(query.lower().split())
    scored: list[tuple[float, dict[str, str]]] = []
    for r in rows:
        s = score_row(qtok, r)
        if s > 0:
            scored.append((s, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def search_stack(stack: str, query: str, limit: int) -> list[tuple[float, dict[str, str]]]:
    stack = STACK_ALIASES.get(stack.lower(), stack.lower())
    fname = STACK_FILES.get(stack)
    if not fname:
        return []
    rows = read_csv_rows(DATA / fname)
    qtok = set(tokenize(query))
    scored = [(score_row(qtok, r), r) for r in rows]
    scored = [(s, r) for s, r in scored if s > 0]
    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        scored = [(score_row(qtok, r), r) for r in rows]
        scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:limit]


def read_reasoning() -> list[dict[str, str]]:
    return read_csv_rows(DATA / "ui_reasoning.csv")


def box_line(inner_width: int, text: str = "") -> str:
    text = text[:inner_width].ljust(inner_width)
    return f"| {text} |"


def render_design_system_ascii(
    query: str,
    project: str,
    hits: dict[str, list[tuple[float, dict[str, str]]]],
    reasoning: list[dict[str, str]],
) -> str:
    inner = 72
    lines: list[str] = []
    lines.append("+" + "-" * (inner + 2) + "+")
    lines.append(box_line(inner, f"UI/UX Pro Max - Design System: {project or 'Project'}"))
    lines.append(box_line(inner, f"Query: {query}"))
    lines.append(box_line(inner, f"Generated (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}"))
    lines.append("+" + "-" * (inner + 2) + "+")

    if reasoning:
        lines.append(box_line(inner, "Reasoning signals (top matches)"))
        for row in reasoning[:4]:
            blob = " | ".join(f"{k}={v}" for k, v in row.items() if v)
            while len(blob) > inner:
                lines.append(box_line(inner, blob[:inner]))
                blob = blob[inner:]
            lines.append(box_line(inner, blob))
        lines.append("+" + "-" * (inner + 2) + "+")

    for dom in DESIGN_SYSTEM_DOMAINS:
        lines.append(box_line(inner, f"DOMAIN: {dom.upper()}"))
        pairs = hits.get(dom, [])
        if not pairs:
            lines.append(box_line(inner, "(no keyword hit - expand data/*.csv or broaden query)"))
        for s, r in pairs[:5]:
            summary = " | ".join(f"{k}={v}" for k, v in r.items() if v)
            chunk = f"[{s:.1f}] {summary}"
            while chunk:
                lines.append(box_line(inner, chunk[:inner]))
                chunk = chunk[inner:]
        lines.append("+" + "-" * (inner + 2) + "+")

    lines.append(box_line(inner, "Anti-patterns (always avoid)"))
    for ap in [
        "Removing visible focus styles on interactive controls",
        "Icon-only controls without accessible names",
        "Color as the only state indicator",
        "Decorative motion without reduced-motion guard",
        "Raw hex sprinkled in components instead of semantic tokens",
    ]:
        lines.append(box_line(inner, f"- {ap}"))
    lines.append("+" + "-" * (inner + 2) + "+")
    return "\n".join(lines)


def render_design_system_markdown(
    query: str,
    project: str,
    hits: dict[str, list[tuple[float, dict[str, str]]]],
    reasoning: list[dict[str, str]],
) -> str:
    lines: list[str] = []
    title = project or "Project"
    lines.append(f"# Design system - {title}")
    lines.append("")
    lines.append(f"- **Query:** {query}")
    lines.append(f"- **Generated (UTC):** {datetime.now(timezone.utc).isoformat(timespec='seconds')}")
    lines.append("")
    if reasoning:
        lines.append("## Reasoning")
        for row in reasoning[:6]:
            lines.append(f"- {' | '.join(f'**{k}:** {v}' for k, v in row.items() if v)}")
        lines.append("")
    for dom in DESIGN_SYSTEM_DOMAINS:
        lines.append(f"## {dom.title()}")
        pairs = hits.get(dom, [])
        if not pairs:
            lines.append("_No strong keyword match - broaden keywords or extend `data/` CSVs._")
        else:
            for s, r in pairs[:6]:
                lines.append(f"- **({s:.1f})** " + " | ".join(f"`{k}`: {v}" for k, v in r.items() if v))
        lines.append("")
    lines.append("## Anti-patterns")
    for ap in [
        "Removing visible focus styles on interactive controls",
        "Icon-only controls without accessible names",
        "Color as the only state indicator",
        "Decorative motion without reduced-motion guard",
        "Raw hex sprinkled in components instead of semantic tokens",
    ]:
        lines.append(f"- {ap}")
    lines.append("")
    return "\n".join(lines)


def persist_design_system(
    content: str,
    project: str,
    page: str | None,
    fmt: str,
) -> None:
    base = Path.cwd() / "design-system"
    base.mkdir(parents=True, exist_ok=True)
    master = base / "MASTER.md"
    master.write_text(content, encoding="utf-8")
    if page:
        pdir = base / "pages"
        pdir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9_-]+", "-", page.strip().lower()).strip("-") or "page"
        pfile = pdir / f"{slug}.md"
        pbody = f"# Page override - {page}\n\n"
        pbody += f"_Overrides for this page only. Master: `../MASTER.md`._\n\n"
        pbody += "## Overrides\n\n- (edit) layout density\n- (edit) component variants\n"
        if fmt == "markdown":
            pbody += "\n## Notes from search\n\n" + content
        pfile.write_text(pbody, encoding="utf-8")


def parallel_domain_search(query: str, limit: int) -> dict[str, list[tuple[float, dict[str, str]]]]:
    out: dict[str, list[tuple[float, dict[str, str]]]] = {}
    with ThreadPoolExecutor(max_workers=len(DESIGN_SYSTEM_DOMAINS)) as ex:
        futs = {ex.submit(search_domain, d, query, limit): d for d in DESIGN_SYSTEM_DOMAINS}
        for fut in as_completed(futs):
            d = futs[fut]
            out[d] = fut.result()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="UI/UX Pro Max domain search")
    ap.add_argument("query", nargs="*", help="Search keywords")
    ap.add_argument("--domain", "-d", choices=sorted(DOMAIN_FILES.keys()), help="Single domain")
    ap.add_argument("--stack", "-s", help="Stack-specific CSV (see SKILL.md list)")
    ap.add_argument("--design-system", action="store_true", help="Synthesize multi-domain recommendations")
    ap.add_argument("--persist", action="store_true", help="Write design-system/MASTER.md (+ optional page)")
    ap.add_argument("-p", "--project", default="", help="Project name label")
    ap.add_argument("--page", default="", help="Page slug for persisted override file")
    ap.add_argument("-n", "--limit", type=int, default=10, help="Max rows per domain/stack")
    ap.add_argument("-f", "--format", choices=("ascii", "markdown"), default="ascii")
    args = ap.parse_args()
    query = " ".join(args.query).strip()
    if not query and not args.design_system:
        ap.print_help()
        return 1

    limit = max(1, min(args.limit, 50))

    if args.stack:
        stack = STACK_ALIASES.get(args.stack.lower(), args.stack.lower())
        if stack not in STACK_FILES:
            print(f"Unknown stack `{args.stack}`. Choose: {', '.join(STACK_FILES)}", file=sys.stderr)
            return 2
        rows = search_stack(stack, query, limit)
        print(f"# stack:{stack}  query:{query!r}\n")
        for s, r in rows:
            print(f"score={s:.2f} :: " + " | ".join(f"{k}={v}" for k, v in r.items() if v))
        return 0

    if args.domain:
        rows = search_domain(args.domain, query, limit)
        print(f"# domain:{args.domain}  query:{query!r}\n")
        for s, r in rows:
            print(f"score={s:.2f} :: " + " | ".join(f"{k}={v}" for k, v in r.items() if v))
        return 0

    if args.design_system:
        hits = parallel_domain_search(query, limit)
        reasoning = read_reasoning()
        r_scored = [(score_row(set(tokenize(query)), row), row) for row in reasoning]
        r_scored.sort(key=lambda x: x[0], reverse=True)
        reasoning_top = [r for s, r in r_scored if s > 0][:8]
        if not reasoning_top:
            reasoning_top = reasoning[:8]

        if args.format == "markdown":
            text = render_design_system_markdown(query, args.project, hits, reasoning_top)
        else:
            text = render_design_system_ascii(query, args.project, hits, reasoning_top)
        print(text)
        if args.persist:
            persist_design_system(text, args.project, args.page or None, args.format)
            print(f"\nWrote {Path.cwd() / 'design-system' / 'MASTER.md'}", file=sys.stderr)
            if args.page:
                slug = re.sub(r"[^a-z0-9_-]+", "-", args.page.strip().lower()).strip("-")
                print(f"Wrote page override design-system/pages/{slug}.md", file=sys.stderr)
        return 0

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
