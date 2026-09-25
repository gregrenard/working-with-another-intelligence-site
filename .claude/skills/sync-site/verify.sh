#!/usr/bin/env bash
# verify.sh — post-deploy sanity checks. Exits non-zero if anything is wrong.
# Safe to run standalone:  bash .claude/skills/sync-site/verify.sh
# Adapted from gregory-renard-site: gate (f) lists THIS repo's permanent files,
# gate (g) (Greg's footer label) is dropped, gate (i) reads the domain from
# pages.json, and gate (j) warns while the book page's forms are not wired.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SKILL_DIR/../../.." && pwd)"
cd "$REPO"

SUBPAGES="$(python3 "$SKILL_DIR/manifest.py" subpages | tr '\n' ' ')"
CONTENT="$(python3 "$SKILL_DIR/manifest.py" content  | tr '\n' ' ')"
STUBS="$(python3   "$SKILL_DIR/manifest.py" stubs    | tr '\n' ' ')"
VARIANTS="$(python3 "$SKILL_DIR/manifest.py" variants | tr '\n' ' ')"
fail=0

echo "--- (a) extension gone + no accidental .// ---"
if grep -rl "\.dc\.html" *.html >/dev/null 2>&1; then echo "  BAD: .dc.html still present"; fail=1; else echo "  ok: extensionless"; fi
if grep -rn '\.//' *.html >/dev/null 2>&1;        then echo "  BAD: .// found";            fail=1; else echo "  ok: no .//"; fi

echo "--- (b) index.html is the homepage (not a redirect) ---"
[ "$(grep -c 'http-equiv="refresh"' index.html)" = "0" ] && echo "  ok: no refresh redirect" || { echo "  BAD: index has refresh"; fail=1; }
[ "$(grep -c '<x-dc>' index.html)" -ge 1 ]               && echo "  ok: <x-dc> present"      || { echo "  BAD: no <x-dc>"; fail=1; }

echo "--- (c) static SEO present: each content page has <title> + og:title inside <head> ---"
cfail=0
for f in index.html $(for n in $CONTENT $VARIANTS; do echo "$n.html"; done); do
  h=$(awk 'BEGIN{p=1}/<body/{p=0}{if(p)print}' "$f")
  if echo "$h" | grep -q "<title>" && echo "$h" | grep -q "og:title"; then :; else echo "  MISS seo-head: $f"; fail=1; cfail=1; fi
done
[ $cfail -eq 0 ] && echo "  ok: all content pages have <title> + og:title in <head>"
echo "--- (c2) redirect stubs carry a refresh + canonical ---"
for n in $STUBS; do
  [ -f "$n.html" ] || continue
  if grep -q 'http-equiv="refresh"' "$n.html" && grep -q 'rel="canonical"' "$n.html"; then echo "  ok: $n redirect stub"; else echo "  WARN: $n missing refresh/canonical"; fi
done

echo "--- (d) every internal page link resolves to a .html file ---"
for n in $SUBPAGES; do
  if grep -qhoE "href=\"$n\"|url: '$n'" *.html 2>/dev/null; then
    [ -f "$n.html" ] && echo "  ok: $n" || { echo "  MISS: $n.html"; fail=1; }
  fi
done
[ -z "$SUBPAGES" ] && echo "  ok: single-page site (no subpages)"

echo "--- (e) every local asset reference resolves ---"
for t in $(grep -rhoE "assets/[A-Za-z0-9%@_./-]+\.(png|jpg|jpeg|webp|gif|svg|mp4|mp3|pdf)" *.html 2>/dev/null | sort -u); do
  [ -f "$t" ] && echo "  ok: $t" || { echo "  MISS: $t"; fail=1; }
done

echo "--- (f) permanent repo files intact (must NOT be clobbered by a sync) ---"
for pf in 404.html CNAME robots.txt sitemap.xml llms.txt support.js; do
  [ -f "$pf" ] && echo "  ok: $pf" || { echo "  BAD: $pf MISSING"; fail=1; }
done
SITE_HOST="$(python3 -c "import sys; sys.path.insert(0,'$SKILL_DIR'); from manifest import SITE; print(SITE.split('//')[1])")"
[ "$(tr -d '[:space:]' < CNAME)" = "$SITE_HOST" ] && echo "  ok: CNAME = $SITE_HOST" || { echo "  BAD: CNAME does not match pages.json site ($SITE_HOST)"; fail=1; }
grep -q "Sitemap: https://$SITE_HOST/sitemap.xml" robots.txt && echo "  ok: robots.txt Sitemap line" || { echo "  BAD: robots.txt Sitemap line wrong"; fail=1; }

echo "--- (h) static pre-render mirror present + resolved (no {{ }} inside it) ---"
for f in index.html $(for n in $CONTENT $VARIANTS; do echo "$n.html"; done); do
  python3 - "$f" <<'PY' || fail=1
import sys, re
f = sys.argv[1]; s = open(f, encoding="utf-8").read()
m = re.search(r"<!--dc-prerender-start-->(.*?)<!--dc-prerender-end-->", s, re.S)
if not m:
    print("  MISS pre-render mirror:", f); sys.exit(1)
if 'id="dc-prerender-css"' not in s:
    print("  MISS swap CSS:", f); sys.exit(1)
ph = len(re.findall(r"\{\{[^}]*\}\}", m.group(1)))
if ph:
    print("  BAD: %d unresolved {{ }} inside mirror: %s" % (ph, f)); sys.exit(1)
print("  ok:", f)
PY
done

echo "--- (k) languages: each URL declares its own lang, canonical and both hreflang ---"
python3 - <<'PYK' || fail=1
import re, sys
bad = 0
for f, lang, canon in (("index.html", "en", "/"), ("fr.html", "fr", "/fr")):
    try:
        s = open(f, encoding="utf-8").read()
    except FileNotFoundError:
        print("  BAD: %s missing" % f); bad = 1; continue
    head = s.split("<body", 1)[0]
    ok = ('<html lang="%s">' % lang) in s \
        and re.search(r'rel="canonical" href="[^"]*%s"' % re.escape(canon), head) \
        and 'hreflang="fr" href="https://working-with-another-intelligence.com/fr"' in head \
        and 'hreflang="en"' in head
    print(("  ok: " if ok else "  BAD: ") + f + " (lang=%s, canonical %s, hreflang en+fr)" % (lang, canon))
    bad |= (not ok)
sys.exit(bad)
PYK

echo "--- (i) pages.json == sitemap.xml == llms.txt (three-way, both directions) ---"
python3 - "$SKILL_DIR" <<'PY2' || fail=1
import re, sys
sys.path.insert(0, sys.argv[1])
from manifest import sitemap_urls, SITE

def norm(u):
    u = u.split("#")[0].split("?")[0].rstrip("/")
    return u if u else SITE

want = {norm(u) for u in sitemap_urls()}
sm = {norm(m) for m in re.findall(r"<loc>([^<]+)</loc>", open("sitemap.xml", encoding="utf-8").read())}
txt = open("llms.txt", encoding="utf-8").read()
m = re.search(r"^## Pages\s*$(.*?)(?=^## |\Z)", txt, re.S | re.M)
if not m:
    print("  BAD: llms.txt has no '## Pages' section"); sys.exit(1)
ll = {norm(u) for u in re.findall(r"\]\((" + re.escape(SITE) + r"[^)]*)\)", m.group(1))}
bad = 0
for label, got in (("sitemap.xml", sm), ("llms.txt", ll)):
    for u in sorted(want - got):
        print("  BAD: in pages.json but missing from %s: %s" % (label, u)); bad = 1
    for u in sorted(got - want):
        print("  BAD: in %s but not a content page in pages.json: %s" % (label, u)); bad = 1
if bad:
    sys.exit(1)
print("  ok: pages.json, sitemap.xml and llms.txt agree on the same %d URLs" % len(want))
PY2

echo "--- (j) forms wired to a real endpoint (WARN until the endpoint exists) ---"
if grep -q 'data-form-endpoint=' index.html 2>/dev/null; then
  echo "  ok: forms wired"
else
  echo "  WARN: the 3 forms (free extract / reserve / invite) show a success state but send"
  echo "        nothing. Wire a dedicated endpoint for THIS site before launch (see SKILL.md)."
fi

echo
[ $fail -eq 0 ] && echo "VERIFY: all checks passed ✅" || echo "VERIFY: FAILURES above ❌"
exit $fail
