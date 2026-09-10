#!/usr/bin/env python3
"""Turn a recipe URL or pasted caption into a markdown file in recipes/.

Inputs come from environment variables set by the workflow:
    RECIPE_URL         page or video URL (optional)
    RECIPE_TEXT        pasted caption or recipe text (optional)
    RECIPE_SOURCE_URL  attribution link when RECIPE_TEXT is used (optional)
    ANTHROPIC_API_KEY  API key

Exactly one of RECIPE_URL or RECIPE_TEXT must be set.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import trafilatura
from anthropic import Anthropic

MODEL = "claude-sonnet-5"
NO_RECIPE = "NO_RECIPE_FOUND"
RECIPES_DIR = Path("recipes")
SOURCES_DIR = Path("sources")

PROMPT = f"""You convert source material into a single markdown recipe file.

Rules:
- Return markdown only. No preamble, no explanation, no code fences.
- Write in the same language as the source material. Do NOT translate.
  If the source is Korean, the entire output including headings stays Korean.
- Ignore hashtags, emoji spam, follow requests, affiliate links and other
  promotional filler. Keep only recipe content.
- Do not invent quantities, times or steps that are not in the source. If a
  quantity is genuinely absent, write it as it was described.
- If the source contains no recipe at all, return exactly {NO_RECIPE} and
  nothing else.
- If the source contains more than one recipe, use the first complete one.

Output this exact structure:

---
title: <recipe title in the source language>
slug: <lowercase ascii, hyphenated, romanized if the title is not ascii>
source_url: <url or empty>
language: <ISO code, e.g. ko or en>
servings: <text or empty>
total_time: <text or empty>
tags: [<two to five short lowercase tags in english>]
captured_at: <YYYY-MM-DD>
---

# <title>

## Ingredients
- <one per line, quantity first>

## Instructions
1. <one step per line>

## Notes
<optional; omit the heading entirely if there is nothing worth noting>
"""


def clean_vtt(raw: str) -> str:
    """Strip cue timings, positioning tags and repeated lines from a VTT file."""
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if "-->" in line or re.fullmatch(r"\d+", line):
            continue
        line = re.sub(r"<[^>]+>", "", line)
        if lines and lines[-1] == line:
            continue
        lines.append(line)
    return "\n".join(lines)


def from_youtube(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                "yt-dlp",
                "--skip-download",
                "--write-subs",
                "--write-auto-subs",
                "--sub-langs", "ko,en,en-orig",
                "--sub-format", "vtt",
                "--write-info-json",
                "-o", f"{tmp}/video",
                url,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        parts = []
        info = Path(tmp, "video.info.json")
        if info.exists():
            data = json.loads(info.read_text())
            parts.append(f"TITLE: {data.get('title', '')}")
            # Creators very often put the full recipe in the description.
            parts.append(f"DESCRIPTION:\n{data.get('description', '')}")
        subs = sorted(Path(tmp).glob("video.*.vtt"))
        if subs:
            parts.append("TRANSCRIPT:\n" + clean_vtt(subs[0].read_text()))
        return "\n\n".join(p for p in parts if p.strip())


def from_web(url: str) -> str:
    host = urlparse(url).netloc.lower()
    # Naver serves the post body inside an iframe; the mobile host does not.
    if "blog.naver.com" in host and not host.startswith("m."):
        url = url.replace("://blog.naver.com", "://m.blog.naver.com")
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise RuntimeError(f"Could not fetch {url}")
    text = trafilatura.extract(
        downloaded, include_comments=False, include_tables=True
    )
    if not text or len(text.strip()) < 80:
        raise RuntimeError(f"Extracted almost no text from {url}")
    return text


def gather_source() -> tuple[str, str]:
    """Return (raw_text, source_url)."""
    url = (os.environ.get("RECIPE_URL") or "").strip()
    text = (os.environ.get("RECIPE_TEXT") or "").strip()
    source_url = (os.environ.get("RECIPE_SOURCE_URL") or "").strip()

    if text:
        if len(text) < 40:
            raise RuntimeError("Pasted text is too short to be a recipe")
        return text, source_url
    if not url:
        raise RuntimeError("Neither RECIPE_URL nor RECIPE_TEXT was provided")

    host = urlparse(url).netloc.lower()
    if "youtube.com" in host or "youtu.be" in host:
        return from_youtube(url), url
    return from_web(url), url


def structure(raw: str, source_url: str) -> str:
    client = Anthropic()
    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        system=PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"source_url: {source_url or '(none)'}\n"
                f"today: {date.today().isoformat()}\n\n"
                f"SOURCE MATERIAL:\n{raw[:120000]}"
            ),
        }],
    )
    return "".join(b.text for b in message.content if b.type == "text").strip()


def slug_from(markdown: str) -> str:
    match = re.search(r"^slug:\s*(.+)$", markdown, re.MULTILINE)
    candidate = match.group(1).strip().strip("\"'") if match else ""
    candidate = re.sub(r"[^a-z0-9-]+", "-", candidate.lower()).strip("-")
    return candidate or f"recipe-{date.today().isoformat()}"


def unique_path(directory: Path, slug: str, suffix: str) -> Path:
    path = directory / f"{slug}{suffix}"
    n = 2
    while path.exists():
        path = directory / f"{slug}-{n}{suffix}"
        n += 1
    return path


def main() -> int:
    raw, source_url = gather_source()
    markdown = structure(raw, source_url)

    if NO_RECIPE in markdown or not markdown:
        print(f"No recipe found in source: {source_url or '(pasted text)'}")
        return 1

    RECIPES_DIR.mkdir(exist_ok=True)
    SOURCES_DIR.mkdir(exist_ok=True)

    slug = slug_from(markdown)
    recipe_path = unique_path(RECIPES_DIR, slug, ".md")
    recipe_path.write_text(markdown + "\n", encoding="utf-8")

    # Keeping the raw input means you can regenerate every recipe later
    # after improving the prompt, without re-scraping anything.
    source_path = SOURCES_DIR / f"{recipe_path.stem}.txt"
    source_path.write_text(
        f"source_url: {source_url}\n\n{raw}\n", encoding="utf-8"
    )

    print(f"Wrote {recipe_path}")
    if out := os.environ.get("GITHUB_OUTPUT"):
        with open(out, "a", encoding="utf-8") as handle:
            handle.write(f"slug={recipe_path.stem}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # surfaced by the workflow's issue-on-failure step
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
