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

### From the website (recommended)

Click **+ Add a recipe** on the site, paste the recipe, and submit. Behind
the scenes this creates a GitHub issue; the **Add recipe** Action formats it
into markdown, commits it to `recipes/`, updates `recipes.json`, and the Pages
workflow redeploys. The recipe appears a minute or two later.

Because the site is static, the form needs a GitHub token to submit:

1. Create a [fine-grained personal access token](https://github.com/settings/personal-access-tokens/new)
   scoped to this repository with **Contents and Issues: Read and write**
   (Issues to add a recipe, Contents to edit one).
2. Paste it into the form and click **Save token**. It is stored only in your
   browser (`localStorage`) and is sent only to `api.github.com` — never
   committed to the repo. Use **Remove token** to clear it.

## Editing a recipe

Open a recipe on the site and click **Edit**. The raw markdown loads in a
text box; make your changes and click **Save changes**. This commits the file
straight to the repo via the GitHub Contents API (using the same saved token,
which needs **Contents: Read and write**), and the site updates after the
Pages redeploy. The `Sync manifest` workflow refreshes `recipes.json` if a
title changed.

### From GitHub directly

You can also open a new issue using the **Add a recipe** form
(Issues → New issue) and submit the recipe there.

The formatter keeps the text as provided (no AI); it only rewrites uncommon
bullet characters and `1)` numbering into markdown equivalents.

You can also add a recipe by hand:

1. Add a markdown file to `recipes/`.
2. Run `python scripts/build_manifest.py` to update `recipes.json`.
