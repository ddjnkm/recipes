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

The easiest way is to paste the text: open a new issue using the **Add a
recipe** form (Issues → New issue), paste the recipe, and submit. A GitHub
Action formats it into markdown, commits it to `recipes/`, updates
`recipes.json`, and closes the issue with a link. The Pages workflow then
redeploys the site.

Formatting is rule-based (no AI):

- The first line, or the optional Title field, becomes the recipe title.
- Lines starting with a bullet (`-`, `*`, `•`) become a markdown list.
- Numbered lines (`1.`, `2)`) become steps.
- Blank lines separate paragraphs.

You can also add a recipe by hand:

1. Add a markdown file to `recipes/`.
2. Run `python scripts/build_manifest.py` to update `recipes.json`.
