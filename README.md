# working-with-another-intelligence.com

Site of the book **Working with Another Intelligence — An AI Reality Test and Management Reality Check**, by Marylène Delbourg-Delphis and Gregory Renard. A static site served by GitHub Pages at **https://working-with-another-intelligence.com**.

This is a **new, standalone site**, not gregory-renard.com. It links out to each author's personal site (delbourg-delphis.org, gregory-renard.com). Its deploy pipeline is adapted from `gregory-renard-site` (see that repo's `ADAPT-THIS-SETUP.md`).

## How this repo relates to Claude Design

**Claude Design is the source of truth**, not this repo. The page is authored in the Claude Design project "Site du livre « Working with Another Intelligence »" (projectId `7daaebae-3d63-4762-8e3c-099fed1efa18`). This repo holds the **deployed output**: the Design page plus deploy-only transforms Claude Design cannot express (clean root URL, static SEO head, static pre-render for no-JS crawlers).

**Never edit `index.html` by hand.** The next sync overwrites it. Content changes go in Claude Design; deploy behaviour goes in `.claude/skills/sync-book-site/`.

## Updating the site

Run the `sync-book-site` skill (`.claude/skills/sync-book-site/SKILL.md`), e.g. « mets à jour le site du livre ». It runs end to end with no approval stop:

1. pull from Claude Design;
2. re-apply every transform;
3. run the gates: layout 390/768/1440 × EN/FR, languages, SEO, LLM-SEO, guardrails;
4. commit, then push if no blocking gate failed;
5. verify the live site;
6. end with a debrief summary.

Standing push authorization for this repo only (Gregory, 2026-09-26).

## Structure

| File | What it is |
|---|---|
| `index.html` | Generated: the Design home, transformed and pre-rendered |
| `support.js` | The Claude Design runtime (vendored, generated, never edit) |
| `assets/` | Author portraits (full-resolution originals; Design copies cannot be pulled over 256 KiB) |
| `CNAME`, `robots.txt`, `sitemap.xml`, `llms.txt`, `404.html` | Repo-only files; a sync must never clobber them. `llms.txt` is hand-written |
| `fr.html` | Generated: the French URL `/fr` (book-seo.py) |
| `.claude/skills/sync-book-site/` | The sync pipeline: `pages.json` (the only page list), `deploy.sh`, `verify.sh` (gates a–m), `check-layout.py`, `check-seo.py`, `verify-live.sh`… |

## Current mode: draft

Served without a custom domain at https://gregrenard.github.io/working-with-another-intelligence-site/ (FR: `/fr`), noindex, no `CNAME` (`"draft": true` in `pages.json`). To launch: `"draft": false`, restore `CNAME`, redeploy, point the DNS.

## Before launch

- **Forms are not wired.** The three forms (free extract, reserve, invite) send nothing yet (verify gate (j)). See `SKILL.md` → "Forms".
- **Design `github.md`** still points at gregory-renard-site: update it in Claude Design.

## Preview locally

```
python3 -m http.server 8765    # then open http://localhost:8765/
```
The runtime needs HTTP, not `file://`.
