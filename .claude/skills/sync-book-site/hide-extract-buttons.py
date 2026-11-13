#!/usr/bin/env python3
"""Deploy-only transform: remove the "Read the introduction and Chapter 1 free" buttons.

Nothing sends the free extract yet, so the buttons that promise it are hidden for now
(site-config.json "hideExtractButtons": true). They are the two links to #extract whose text is
{{ t.heroExtract }}: the hero button and the link shown after a reservation. The page's "Free
chapter" section and its form are untouched.

Run from the repo root on index.html and fr.html, after book-seo.py and BEFORE prerender.py, so the
static mirror does not carry them. Idempotent. With the flag on, it fails if the template no
longer holds exactly 2 such links (Design changed): look at the page rather than guessing.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if not json.load(open(os.path.join(HERE, "site-config.json"), encoding="utf-8")).get("hideExtractButtons"):
    print("extract buttons: shown (hideExtractButtons is false)")
    sys.exit(0)

LINK = re.compile(r'[ \t]*<a [^>]*href="#extract"[^>]*>\{\{ t\.heroExtract \}\}</a>[ \t]*\n?')
for page in ("index.html", "fr.html"):
    s = open(page, encoding="utf-8").read()
    new, n = LINK.subn("", s)
    if n not in (0, 2):
        sys.exit("extract buttons: expected 2 links in %s, found %d (Design changed it?)" % (page, n))
    if n == 0 and "{{ t.heroExtract }}" in s:
        sys.exit("extract buttons: %s still uses t.heroExtract in a different shape" % page)
    open(page, "w", encoding="utf-8").write(new)
print("extract buttons: hidden in index.html and fr.html")
