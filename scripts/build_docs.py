#!/usr/bin/env python3
"""Generate docs/index.html by listing all tools in tools/*.

Reads tools/<x>/metadata.json when it exists (otherwise it just uses the folder name) and produces a
simple static page. Called by the `.github/workflows/pages.yml` workflow on each push to main.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
DOCS_DIR = ROOT / "docs"

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WorldAces Community Tools</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 780px; margin: 3rem auto; padding: 0 1rem; color: #1a1f26; }}
  h1 {{ margin-bottom: 0.2rem; }}
  .sub {{ color: #5a6472; margin-top: 0; }}
  .card {{ border: 1px solid #e2e6eb; border-radius: 10px; padding: 1rem 1.2rem; margin: 1rem 0; }}
  .card h2 {{ margin: 0 0 0.3rem 0; font-size: 1.1rem; }}
  .tags span {{ display: inline-block; background: #eef1f5; border-radius: 999px; padding: 0.15rem 0.6rem; font-size: 0.78rem; margin-right: 0.3rem; color: #444; }}
  a {{ color: #2a67c9; }}
</style>
</head>
<body>
<h1>WorldAces Community Tools</h1>
<p class="sub">Tools shared by the community. Click a tool for instructions.</p>
{cards}
</body>
</html>
"""

CARD_TEMPLATE = """<div class="card">
  <h2><a href="https://github.com/{repo}/tree/main/tools/{slug}">{name}</a></h2>
  <p>{description}</p>
  <div class="tags">{tags}</div>
  <p><small>by {author}</small></p>
</div>
"""


def main():
    repo = "ORG/worldaces-community-tools"  # replace after repo creation
    cards = []
    for tool_dir in sorted(TOOLS_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        meta_path = tool_dir / "metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
        else:
            meta = {"name": tool_dir.name, "description": "", "author": "?", "tags": []}
        tags = "".join(f"<span>{t}</span>" for t in meta.get("tags", []))
        cards.append(CARD_TEMPLATE.format(
            repo=repo, slug=tool_dir.name, name=meta.get("name", tool_dir.name),
            description=meta.get("description", ""), tags=tags,
            author=meta.get("author", "?"),
        ))

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(TEMPLATE.format(cards="\n".join(cards)))
    print(f"wrote docs/index.html with {len(cards)} tool(s)")


if __name__ == "__main__":
    main()
