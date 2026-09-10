#!/usr/bin/env python3
"""Turn pasted recipe text into a markdown file in recipes/.

Input comes from a GitHub issue created with the "Add a recipe" form. The
workflow passes the issue body in the ISSUE_BODY environment variable; this
script pulls out the form fields, applies light rule-based formatting (no AI),
writes recipes/<slug>.md, and rebuilds the site manifest.
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

RECIPES_DIR = Path("recipes")
NO_RESPONSE = "_no response_"


def parse_issue_body(body: str) -> dict:
    """Split a GitHub issue-form body into {field: value} by its ### headings.

    The form renders each field as a '### Label' heading followed by the value,
    or '_No response_' when an optional field was left blank.
    """
    fields: dict[str, str] = {}
    current = None
    chunk: list[str] = []

    def flush():
        if current is not None:
            value = "\n".join(chunk).strip()
            if value.lower() == NO_RESPONSE:
                value = ""
            fields[current] = value

    for line in body.replace("\r\n", "\n").split("\n"):
        heading = re.match(r"^###\s+(.+?)\s*$", line)
        if heading:
            flush()
            current = heading.group(1).strip().lower()
            chunk = []
        else:
            chunk.append(line)
    flush()
    return fields


def gather_input() -> tuple[str, str, str]:
    """Return (title, text, source_url) from the issue body or env vars."""
    body = os.environ.get("ISSUE_BODY") or ""
    fields = parse_issue_body(body)

    title = ""
    text = ""
    source_url = ""
    for key, value in fields.items():
        if key.startswith("title"):
            title = value
        elif key.startswith("recipe"):
            text = value
        elif key.startswith("source"):
            source_url = value

    # Fallbacks so the script also works from a plain env-var invocation.
    text = text or (os.environ.get("RECIPE_TEXT") or "").strip()
    title = title or (os.environ.get("RECIPE_TITLE") or "").strip()
    source_url = source_url or (os.environ.get("RECIPE_SOURCE_URL") or "").strip()
    return title.strip(), text.strip(), source_url.strip()


def format_body(text: str) -> str:
    """Light, predictable markdown formatting. No content is invented."""
    out: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            out.append("")
            continue

        # Normalize common bullet characters into markdown list items.
        bullet = re.match(r"^[\-\*•‣▪・·]\s+(.*)$", stripped)
        if bullet:
            out.append(f"- {bullet.group(1).strip()}")
            continue

        # Normalize "1)" / "1." / "1 -" numbered lines into ordered list items.
        numbered = re.match(r"^(\d+)[.)]\s+(.*)$", stripped)
        if numbered:
            out.append(f"{numbered.group(1)}. {numbered.group(2).strip()}")
            continue

        out.append(stripped)

    # Collapse runs of blank lines down to a single separator.
    cleaned: list[str] = []
    for line in out:
        if line == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def slugify(title: str) -> str:
    """Lowercase, hyphenated slug that keeps unicode letters (e.g. Korean)."""
    slug = re.sub(r"[^\w]+", "-", title.lower(), flags=re.UNICODE).strip("-")
    return slug or f"recipe-{date.today().isoformat()}"


def unique_path(directory: Path, slug: str, suffix: str) -> Path:
    path = directory / f"{slug}{suffix}"
    n = 2
    while path.exists():
        path = directory / f"{slug}-{n}{suffix}"
        n += 1
    return path


def build_markdown(title: str, body: str, source_url: str) -> str:
    lines = ["---", f"title: {title}"]
    if source_url:
        lines.append(f"source_url: {source_url}")
    lines.append(f"captured_at: {date.today().isoformat()}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(body)
    if source_url:
        lines.append("")
        lines.append(f"[Source]({source_url})")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    title, text, source_url = gather_input()

    if not text:
        print("ERROR: No recipe text was provided", file=sys.stderr)
        return 1

    # If no title was given, use the first non-empty line and drop it from body.
    if not title:
        for i, line in enumerate(text.split("\n")):
            if line.strip():
                title = line.strip().lstrip("#").strip()
                text = "\n".join(text.split("\n")[i + 1:])
                break
    if not title:
        title = f"Recipe {date.today().isoformat()}"

    body = format_body(text)
    if not body:
        print("ERROR: Nothing left to write after formatting", file=sys.stderr)
        return 1

    RECIPES_DIR.mkdir(exist_ok=True)
    slug = slugify(title)
    recipe_path = unique_path(RECIPES_DIR, slug, ".md")
    recipe_path.write_text(build_markdown(title, body, source_url), encoding="utf-8")

    # Rebuild the manifest the website reads so the new recipe shows up.
    import build_manifest
    build_manifest.main()

    print(f"Wrote {recipe_path}")
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(f"slug={recipe_path.stem}\n")
            handle.write(f"file={recipe_path.name}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # surfaced by the workflow's failure comment
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
