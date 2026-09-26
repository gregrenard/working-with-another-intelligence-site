#!/usr/bin/env bash
# deploy.sh — re-apply ALL deploy-only transforms after pulling the *.dc.html pages
# from Claude Design (via extract-pulled.py), then verify. Idempotent.
#
# Adapted from gregory-renard-site (see its ADAPT-THIS-SETUP.md). Stages kept: the
# structural ones (1, 2, 4, 5, 6, 7). Dropped: Greg's contact-form patch, his SEO
# enrichment, his hero-wrap CSS fix and his gallery .png->.jpg rename — all specific
# to his site. The book page's three forms are NOT wired yet (see SKILL.md, "Forms").
#
# Pipeline order is critical (see SKILL.md):
#   cp Home->index -> home-link ./ -> seo-clean-urls -> layout-fix -> book-seo (fr.html) -> rename *.dc.html->*.html
#   (+ rm Home) -> bump sitemap -> prerender (LAST) -> verify
#
# Does NOT touch the permanent repo files (404.html, CNAME, robots.txt, sitemap.xml
# content, llms.txt, support.js) — they are not from Design and must survive every sync.
#
# Usage:  bash .claude/skills/sync-book-site/deploy.sh      (run from anywhere)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"
cd "$REPO"

# Page lists come from pages.json via manifest.py — never re-hardcode them here.
# HOME_SRC is read as a whole line: the Design home filename contains spaces.
HOME_SRC="$(python3 "$SKILL_DIR/manifest.py" home-design)"
SUBPAGES="$(python3 "$SKILL_DIR/manifest.py" subpages | tr '\n' ' ')"
# The home as Design links to it: spaces percent-encoded (e.g. "Working%20with%20…dc.html")
HOME_URL="$(python3 -c 'import sys,urllib.parse; print(urllib.parse.quote(sys.argv[1]))' "$HOME_SRC")"
HOME_RE="$(printf '%s' "$HOME_URL" | sed 's/[.[\*^$/]/\\&/g')"

[ -f "$HOME_SRC" ] || { echo "ERROR: '$HOME_SRC' not found — run extract-pulled.py first."; exit 1; }

shopt -s nullglob
DC_FILES=( *.dc.html )

echo "==> 1/6  clean root: index.html = home page"
cp "$HOME_SRC" index.html

echo "==> 2/6  rewrite home link -> ./  (href + JS url forms, quote-anchored)"
sed -i '' "s|\"$HOME_RE\"|\"./\"|g" "${DC_FILES[@]}" index.html
sed -i '' "s|'$HOME_RE'|'./'|g"     "${DC_FILES[@]}" index.html

echo "==> 3/6  forms: NOT wired (no endpoint yet) — see SKILL.md 'Forms'"

echo "==> 4/6  clean URLs + static SEO head"
python3 "$SKILL_DIR/seo-clean-urls.py"

echo "==> 4a/6 layout fix: hero title + stat numbers wrap (mobile overflow, long French title)"
python3 "$SKILL_DIR/layout-fix.py"

echo "==> 4b/6 book SEO: favicon + theme-color, JSON-LD, real French URL /fr (fr.html), language routing"
python3 "$SKILL_DIR/book-seo.py"

echo "==> 5/6  rename *.dc.html -> *.html (+ drop redundant home source)"
for f in $SUBPAGES; do [ -f "$f.dc.html" ] && mv "$f.dc.html" "$f.html"; done
rm -f "$HOME_SRC"

echo "==> 6/6  bump sitemap <lastmod> to today"
TODAY="$(date +%F)"
sed -i '' "s|<lastmod>[^<]*</lastmod>|<lastmod>$TODAY</lastmod>|g" sitemap.xml

echo "==> 7/7  static pre-render (headless): real content for no-JS / non-JS crawlers"
python3 "$SKILL_DIR/prerender.py"

echo
bash "$SKILL_DIR/verify.sh"
