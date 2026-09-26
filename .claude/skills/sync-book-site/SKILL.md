---
name: sync-book-site
description: Publish the latest version of the "Working with Another Intelligence" book site from Claude Design to its GitHub repo (gregrenard/working-with-another-intelligence-site) — pull, re-apply deploy transforms, check desktop/tablet/mobile layout, languages (EN / and FR /fr), SEO, LLM-SEO (llms.txt, AI crawlers, JSON-LD) and content guardrails, commit, push, verify the live site, and end with a debrief summary. Use when the user says "mets à jour le site du livre", "synchronise le site du livre", "publie le site du livre", "récupère la dernière version du site", "sync the book site", "update the book site from Claude Design".
---

# Sync the book site: Claude Design → checks → GitHub → live → debrief

A **standalone site** for the book *Working with Another Intelligence* (Marylène Delbourg-Delphis & Gregory Renard). It is **not** gregory-renard.com. The pipeline is adapted from `gregory-renard-site`; that repo's `ADAPT-THIS-SETUP.md` explains every stage.

## Project facts
- **Source of truth:** Claude Design project "Site du livre « Working with Another Intelligence »", projectId `7daaebae-3d63-4762-8e3c-099fed1efa18`. Type `PROJECT_TYPE_PROJECT`, so **DesignSync is read-only**: only `list_files` and `get_file`, never `finalize_plan` / `write_files` / `delete_files`.
- **Pages** (single source of truth: `pages.json`): the Design home → `index.html` (EN, `/`), plus the generated variant `fr.html` (FR, `/fr`).
- **Repo:** `github.com/gregrenard/working-with-another-intelligence-site` (public), branch `main`, GitHub Pages from `main` root.
- **Mode:** `pages.json` → `"draft": true`. The site is served at `preview_url` (https://gregrenard.github.io/working-with-another-intelligence-site/) with **no custom domain, no CNAME, noindex**. Launch: set `"draft": false`, restore `CNAME` (`working-with-another-intelligence.com`), redeploy, then point the DNS.
- **gh account:** `gregrenard` (`gh auth switch -u gregrenard` if another is active; leave it on `gregrenard` afterwards).
- ⚠️ The Design project's `github.md` names `gregory-renard-site` as its target, a leftover. **Never push this site there.**

## The flow: run it end to end, no stop for approval
Starting the skill is the go. There is no "did you finish editing?" question and no push-approval step. On 2026-09-26 Gregory granted a **standing push authorization for this repo only**, conditional on the gates. The authorization removes the question, not the checks.

1. **Structure:** `DesignSync list_files`, then compare the page files with `python3 .claude/skills/sync-book-site/manifest.py design`. A new or renamed page means updating `pages.json`, then `sitemap.xml` and `llms.txt` (gate (i)); flag it in the debrief.
2. **Pull:** `DesignSync get_file` for each page, plus `support.js` (compare it with the repo copy; replace it only if it changed). Images over 256 KiB come back truncated: keep the repo's working file, never commit a truncated one, and list it in the debrief.
3. **Write byte-exact:** `python3 .claude/skills/sync-book-site/extract-pulled.py <session.jsonl>`. Pass the transcript path when the session was not started inside `website/`. **Never retype a page.**
4. **Deploy + all gates:** `bash .claude/skills/sync-book-site/deploy.sh` (transforms, then `verify.sh`: gates a–m, below).
5. **Review:** `git diff --stat`, then a text-level diff of the Design page against the previous pull, to know what the authors changed. It feeds the commit message and the debrief.
6. **Commit** (English, explains what changed and why, **no Claude attribution**). If `verify.sh` has any **BAD**, stop here: do not push, and go to the debrief.
7. **Push:** `git push origin main` (with `gregrenard`). If rejected: `git -c credential.helper= -c credential.helper='!gh auth git-credential' push origin main`.
8. **Live check:** `bash .claude/skills/sync-book-site/verify-live.sh`. It waits for the Pages build of this commit, then checks HTTP (pages, assets, 404) and a headless render of `/` and `/fr` (lang, `<h1>`, robots mode).
9. **Debrief summary** (always, even when stopped early). Write it in French, short, in this order:
   - **Résultat :** published or not, commit SHA, live links (`/` and `/fr`).
   - **Ce qui a changé dans Claude Design:** 3–6 bullets from step 5.
   - **Contrôles:** one line per family: layout (desktop/tablet/mobile × EN/FR), languages, SEO, LLM-SEO, guardrails, live, each with ✅ or ❌.
   - **Avertissements:** every WARN, grouped (e.g. `{{ }}` placeholders to fill in Design, unwired forms, title too long).
   - **À faire côté auteurs:** only the actions that belong to them, in Claude Design or elsewhere.
   - If it was stopped at a BAD: what failed, why, and the fix.
   Offer a version tag (`vX.Y`) in the debrief. Tags are created only on request, and pushing a tag needs its own go.

## Pipeline (deploy.sh) and ordering constraints
```
1  cp "<Home>.dc.html" index.html            clean root, no redirect
2  home-link rewrite -> "./"                 quote-anchored; name read from pages.json, %20-encoded
3  forms: not wired yet                      see "Forms"
4  seo-clean-urls.py                         strip .dc.html, lift <helmet> into <head>, lang="en"
4a layout-fix.py                             hero title / stat numbers / meta lines may wrap; no horizontal scroll
4b book-seo.py                               favicon + theme-color, JSON-LD, fr.html (/fr), language routing, draft noindex
5  rename *.dc.html -> *.html, rm home source
6  bump sitemap <lastmod>
7  prerender.py                              LAST: static mirror for no-JS crawlers
   verify.sh                                 gates a–m
```
- Pre-render runs **last**. Clean-URLs runs **before** the rename. layout-fix runs before book-seo, so fr.html inherits it.
- `index.html` and `fr.html` are **generated**: never edit them. Fix content in Claude Design.
- book-seo.py localizes only the static `<head>` and the `<helmet>`, **never the component script**. A French apostrophe inside a JS `'…'` literal broke the runtime on 2026-09-24. If Design changes the title, description or language logic, book-seo.py stops with a clear error; update its EN/FR strings and patterns.
- Language routing uses **relative** links (`fr`, `./`), so it works on the github.io project path and on the domain.

## Verify gates (verify.sh)
| Gate | Checks | Blocking |
|---|---|---|
| (a) | no `.dc.html`, no `.//` | yes |
| (b) | index is the home, not a redirect | yes |
| (c) | `<title>` + `og:title` in `<head>` (EN + FR) | yes |
| (d) (e) | internal links and local assets resolve | yes |
| (f) | permanent files present; **draft:** no CNAME, both pages noindex / **launched:** CNAME = domain | yes |
| (h) | pre-render mirror with zero `{{ }}` | yes when launched, **WARN in draft** (pages are noindex) |
| (i) | `pages.json` = `sitemap.xml` = `llms.txt` | yes |
| (j) | forms wired | WARN |
| (k) | languages: `/` lang=en and `/fr` lang=fr, own canonical, hreflang en + fr | yes |
| (l) | **layout** (`check-layout.py`): `/` and `/fr` at 390 / 768 / 1440 px in a true-width iframe (headless Chrome cannot go under 500 px): no horizontal scroll, no unclipped element past the edge, `<h1>` rendered. Visible `{{ }}` = WARN | yes |
| (m) | **SEO + LLM-SEO + guardrails** (`check-seo.py`): title/description lengths (WARN), OG + Twitter tags, og:image 1200×630, JSON-LD Book with 2 authors (Marylène first, both with url), favicon/apple-touch-icon, robots meta matches the mode; robots.txt allows GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, Google-Extended; llms.txt well-formed with both authors; **no real client name or real surname** in any published file (hash-based, because the repo is public) | yes |

After the push, `verify-live.sh` repeats the essentials on the live URL.

## Forms (must be solved before launch)
Three forms (free extract, reserve, invite) show a success state but **send nothing**. Before launch:
1. Choose a destination: **Brevo** (French, GDPR; the list tool in `promotion/04-site-brief-claude-design.md`) or a dedicated Google Apps Script web app.
2. Write `patch-forms.py` (honeypot, double opt-in), mark the page `data-form-endpoint=`, and add it as stage 3.
3. **Never reuse gregory-renard-site's endpoint**: it writes into Greg's personal contact spreadsheet.

## Permanent repo files (not from Design; a sync must never clobber them)
`404.html` (computes its home links, so it works on both hosts), `robots.txt`, `sitemap.xml`, `llms.txt` (hand-written: editorial, never generated), `support.js` (the dc-runtime from this Design project; vendored), `assets/`, and `CNAME` once launched.

## Content guardrails (from `promotion/00-positioning.md`)
- The client is **ACME** in all published text: never the real name, including in alt text, JSON-LD, llms.txt and commit messages (gate (m) enforces it for files).
- Author order is always **Marylène Delbourg-Delphis, then Gregory Renard**.
