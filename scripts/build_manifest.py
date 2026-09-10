#!/usr/bin/env python3
"""Scan recipes/ and write recipes.json, the manifest the website reads.

The static site cannot list a directory on its own, so this script builds a
small JSON index of every markdown recipe. Run it after adding or removing a
recipe; the capture workflow runs it automatically.
"""

import json
import re
from pathlib import Path

RECIPES_DIR = Path("recipes")
MANIFEST = Path("recipes.json")


def title_of(markdown: str, fallback: str) -> str:
    """Prefer a YAML front matter title, then the first heading, then the name."""
    front = re.match(r"^---\s*\n(.*?)\n---\s*\n", markdown, re.DOTALL)
    if front:
        match = re.search(r"^title:\s*(.+)$", front.group(1), re.MULTILINE)
        if match:
            return match.group(1).strip().strip("\"'")
    heading = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if heading:
        return heading.group(1).strip()
    return fallback


def main() -> None:
    recipes = []
    for path in sorted(RECIPES_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        recipes.append({
            "file": path.name,
            "title": title_of(text, path.stem),
        })

    recipes.sort(key=lambda r: r["title"].lower())
    MANIFEST.write_text(
        json.dumps(recipes, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {MANIFEST} with {len(recipes)} recipe(s)")


if __name__ == "__main__":
    main()
