---
name: sync-site
description: Sync the working-with-another-intelligence.com book site from Claude Design to its own GitHub repository, re-applying the deploy-only transforms Claude Design can't do (clean root URL, static SEO head, pre-render mirror) and running the verify gates. Use when the user has edited the book site in claude.ai/design and wants the changes published — triggers like "sync the book site", "mets à jour le site du livre", "j'ai modifié le site du livre dans Claude Design", "publie le site du livre".
---

# Sync the book site — Claude Design → GitHub Pages

This is a **new, standalone site** for the book *Working with Another Intelligence* (Marylène Delbourg-Delphis & Gregory Renard), on its own domain. It is **not** gregory-renard.com. The pipeline is adapted from `gregory-renard-site` (read its `ADAPT-THIS-SETUP.md` for the rationale behind every stage).

## Project facts
- **Source of truth:** Claude Design project "Site du livre « Working with Another Intelligence »", projectId `7daaebae-3d63-4762-8e3c-099fed1efa18`. Type `PROJECT_TYPE_PROJECT`, so **DesignSync is read-only**: only `list_files` and `get_file`, never `finalize_plan` / `write_files` / `delete_files`.
- **Pages:** one, the home, `Working with Another Intelligence.dc.html` → deployed as `index.html` (see `pages.json`).
- **Domain:** https://working-with-another-intelligence.com (`CNAME`).
- **Repository:** to be created under Gregory's personal GitHub account (`gregrenard`), e.g. `gregrenard/working-with-another-intelligence-site`. Not created yet.
- ⚠️ The Design project's `github.md` still names `gregrenard/gregory-renard-site` as its sync target, left over from reusing Greg's conventions. **Never push this site there.**

## Automated flow
Once the user confirms editing in Claude Design is **finished** (DesignSync reads the live project):
1. `DesignSync list_files` → check the page filenames still match `python3 .claude/skills/sync-site/manifest.py design`. A new or renamed page means updating `pages.json`, then `sitemap.xml` and `llms.txt` (gate (i) fails until all three agree).
2. `DesignSync get_file` for each page (and `support.js` if the runtime changed).
3. `python3 .claude/skills/sync-site/extract-pulled.py` → writes the pulled pages byte-exact from the session transcript. **Never retype a page.**
4. `bash .claude/skills/sync-site/deploy.sh` → full pipeline, then `verify.sh`. Every gate must pass. Gate (j) stays a WARN until the forms are wired.
5. Assets: `get_file` is capped at 256 KiB. Images come back truncated (the portraits did on 24 Sep 2026). Keep the working local file and never commit a truncated one. The originals live in `book-cognitive-sovereignty/promotion/assets/`.
6. Review `git diff`, commit (English message explaining what changed and why, **no Claude attribution**).
7. **Push: ASK FIRST.** No standing push authorization exists for this repo (unlike gregory-renard-site). Per Gregory's global rule, `git push` is an outward action that waits for an explicit go, every time. Push with the `gregrenard` gh account (`gh auth switch -u gregrenard`), and switch back afterwards if needed.

## Pipeline (deploy.sh) and its ordering constraints
```
1  cp "<Home>.dc.html" index.html            (clean root, no redirect)
2  home-link rewrite -> "./"                 (quote-anchored; name read from pages.json, %20-encoded)
3  forms: not wired yet                      (see "Forms")
4  seo-clean-urls.py                         (strip .dc.html, lift <helmet> into <head>, lang="en")
5  rename *.dc.html -> *.html, rm home source
6  bump sitemap <lastmod>
7  prerender.py                              (LAST: headless render, static mirror for no-JS crawlers)
   verify.sh                                 (gates a–j)
```
- Pre-render runs **last**. Clean-URLs runs **before** the rename.
- `index.html` is a **generated artifact**: never edit it. Fix content in Claude Design.
- Stages removed from Greg's pipeline, because they are his site in code: contact-form patch (his Google Apps Script endpoint), `enrich-seo.py` (his biography), `hero-wrap-fix.py` (his CSS), and the gallery `.png`→`.jpg` rename.

## Forms (must be solved before launch)
The book page has three forms: the free extract, reserve your copy, and invite. They show a success state but **send nothing**. Before launch:
1. Choose a destination. **Brevo** is recommended: French, GDPR, and it is the list tool proposed in `promotion/04-site-brief-claude-design.md`. The alternative is a dedicated Google Apps Script web app for this site.
2. Write `patch-forms.py` to wire the three forms to that endpoint (honeypot, double opt-in for GDPR), mark the page with `data-form-endpoint=`, and add it as stage 3 of `deploy.sh`.
3. **Never reuse the endpoint from gregory-renard-site**: it writes into Greg's personal contact spreadsheet.

## Verify gates
(a) no `.dc.html` / `.//` · (b) index is the home, not a redirect · (c) `<title>` + `og:title` in `<head>` · (c2) stubs · (d) internal links resolve · (e) local assets resolve · (f) permanent files present, CNAME and robots.txt match the domain in `pages.json` · (h) pre-render mirror with zero `{{ }}` · (i) `pages.json` = `sitemap.xml` = `llms.txt` · (j) forms wired (WARN).

## Permanent repo files (not from Design; a sync must never clobber them)
`CNAME`, `404.html`, `robots.txt`, `sitemap.xml`, `llms.txt` (hand-written: editorial, never generated), `support.js` (the dc-runtime pulled from this Design project; vendored, never edit), `assets/`.

## Content guardrails (from `promotion/00-positioning.md`)
- The client is **ACME** in all published text; never the real name, including in alt text, JSON-LD and llms.txt.
- Author order is always **Marylène Delbourg-Delphis, then Gregory Renard**.
