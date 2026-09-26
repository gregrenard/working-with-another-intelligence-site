#!/usr/bin/env bash
# verify-live.sh — after a push: wait for GitHub Pages to build the pushed commit, then
# check the LIVE site (draft: the github.io preview URL; launched: the real domain).
# Checks: build status, HTTP codes (/, /fr, a missing page -> 404, key assets), and a
# headless render of / and /fr (html lang, <h1> rendered, robots meta matches the mode).
# Usage: bash .claude/skills/sync-book-site/verify-live.sh      (from anywhere)
set -uo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"
cd "$REPO"
LIVE="$(python3 "$SKILL_DIR/manifest.py" live-url)"
DRAFT="$(python3 "$SKILL_DIR/manifest.py" draft)"
SLUG="$(git remote get-url origin | sed -E 's#.*github.com[:/]##; s#\.git$##')"
HEAD_SHA="$(git rev-parse HEAD)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
fail=0

echo "--- live: waiting for GitHub Pages to build $SLUG@${HEAD_SHA:0:7} ---"
for i in $(seq 1 36); do
  read -r st sha < <(gh api "repos/$SLUG/pages/builds/latest" --jq '.status + " " + .commit' 2>/dev/null || echo "unknown x")
  if [ "$sha" = "$HEAD_SHA" ] && [ "$st" = "built" ]; then echo "  ok: built"; break; fi
  if [ "$sha" = "$HEAD_SHA" ] && [ "$st" = "errored" ]; then echo "  BAD: Pages build errored"; fail=1; break; fi
  [ "$i" = 36 ] && { echo "  BAD: build not finished after 6 min (last: $st ${sha:0:7})"; fail=1; }
  sleep 10
done

echo "--- live: HTTP ($LIVE) ---"
code() { curl -s -o /dev/null -w "%{http_code}" "$1"; }
for p in "/" "/fr" "/assets/og-cover.png" "/assets/favicon.png" "/support.js" "/robots.txt" "/llms.txt" "/sitemap.xml"; do
  c="$(code "$LIVE$p")"; [ "$c" = "200" ] && echo "  ok: $p 200" || { echo "  BAD: $p -> $c"; fail=1; }
done
c="$(code "$LIVE/__does-not-exist")"; [ "$c" = "404" ] && echo "  ok: unknown page -> 404" || { echo "  BAD: unknown page -> $c"; fail=1; }

echo "--- live: rendered pages ---"
for spec in "/:en" "/fr:fr"; do
  p="${spec%%:*}"; lang="${spec##*:}"
  "$CHROME" --headless=new --disable-gpu --dump-dom --virtual-time-budget=10000 "$LIVE$p" 2>/dev/null \
  | python3 -c "
import sys, re
s = sys.stdin.read(); lang, draft, p = sys.argv[1], sys.argv[2] == '1', sys.argv[3]
okl = ('<html lang=\"%s\"' % lang) in s
h1 = re.search(r'<h1[^>]*>(.*?)</h1>', s, re.S)
okh = bool(h1 and re.sub(r'<[^>]+>', '', h1.group(1)).strip())
rob = re.findall(r'name=\"robots\" content=\"([^\"]+)\"', s)
okr = bool(rob) and (rob[0].startswith('noindex') if draft else rob[0].startswith('index'))
print(('  ok: ' if okl and okh and okr else '  BAD: ') + '%s lang=%s %s, h1 %s, robots %s' % (p, lang, 'ok' if okl else 'WRONG', 'rendered' if okh else 'MISSING', rob[:1]))
sys.exit(0 if okl and okh and okr else 1)
" "$lang" "$DRAFT" "$p" || fail=1
done

echo
[ $fail -eq 0 ] && echo "LIVE: all checks passed ✅  $LIVE/  ·  $LIVE/fr" || echo "LIVE: FAILURES above ❌"
exit $fail
