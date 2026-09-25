# working-with-another-intelligence.com

Site of the book **Working with Another Intelligence — An AI Reality Test and Management Reality Check**, by Marylène Delbourg-Delphis and Gregory Renard. A static site served by GitHub Pages at **https://working-with-another-intelligence.com**.

This is a **new, standalone site**, not gregory-renard.com. It links out to each author's personal site (delbourg-delphis.org, gregory-renard.com). Its deploy pipeline is adapted from `gregory-renard-site` (see that repo's `ADAPT-THIS-SETUP.md`).

## How this repo relates to Claude Design

**Claude Design is the source of truth**, not this repo. The page is authored in the Claude Design project "Site du livre « Working with Another Intelligence »" (projectId `7daaebae-3d63-4762-8e3c-099fed1efa18`). This repo holds the **deployed output**: the Design page plus deploy-only transforms Claude Design cannot express (clean root URL, static SEO head, static pre-render for no-JS crawlers).

**Never edit `index.html` by hand.** The next sync overwrites it. Content changes go in Claude Design; deploy behaviour goes in `.claude/skills/sync-site/`.

## Updating the site

Run the `/sync-site` skill (`.claude/skills/sync-site/SKILL.md`). It pulls the page from Claude Design, re-applies every transform, runs the verify gates, and commits. **Pushing needs an explicit go each time.**

## Structure

| File | What it is |
|---|---|
| `index.html` | Generated: the Design home, transformed and pre-rendered |
| `support.js` | The Claude Design runtime (vendored, generated, never edit) |
| `assets/` | Author portraits (full-resolution originals; Design copies cannot be pulled over 256 KiB) |
| `CNAME`, `robots.txt`, `sitemap.xml`, `llms.txt`, `404.html` | Repo-only files; a sync must never clobber them. `llms.txt` is hand-written |
| `.claude/skills/sync-site/` | The sync pipeline: `pages.json` (the only page list), `deploy.sh`, `verify.sh`, `prerender.py`… |

## Before launch

- **Forms are not wired.** The three forms (free extract, reserve, invite) send nothing yet (verify gate (j)). See `SKILL.md` → "Forms".
- **GitHub repository:** to be created under `gregrenard`, with Pages enabled and the custom domain pointed at it. The Design project's `github.md` still points at gregory-renard-site: update it there.

## Preview locally

```
python3 -m http.server 8765    # then open http://localhost:8765/
```
The runtime needs HTTP, not `file://`.
