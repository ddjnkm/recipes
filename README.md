# recipes

A barebones static recipes website. Recipes are plain markdown files in
`recipes/`, and `index.html` lists them and renders the selected one in the
browser.

## How it works

- `recipes/*.md` — one markdown file per recipe.
- `recipes.json` — the manifest the site reads (a static page cannot list a
  folder on its own). Rebuild it with `python scripts/build_manifest.py`.
- `index.html` — fetches the manifest, shows the list, and renders a recipe
  in-page.

## Viewing locally

The page fetches local files, so serve it over HTTP rather than opening the
file directly:

```
python3 -m http.server
```

Then open http://localhost:8000/.

## Adding a recipe

1. Add a markdown file to `recipes/`.
2. Run `python scripts/build_manifest.py` to update `recipes.json`.

The `Capture recipe` GitHub Action does both automatically when it captures a
recipe from a URL or pasted text.
