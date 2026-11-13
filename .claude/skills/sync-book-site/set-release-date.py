#!/usr/bin/env python3
"""Deploy-only transform: set the publication date shown on the page.

Design hardcodes the date as the default of the component's `releaseDate` prop:
    const date = this.props.releaseDate || (lang === 'fr' ? '1er décembre 2026' : '1 December 2026');
Claude Design is read-only for this project, so the date is rewritten here from
site-config.json ("releaseDate": {"en", "fr"}). It feeds the top bar ("Pre-orders open: out ..."),
the hero line and the pre-order text, in both languages.

Run from the repo root on index.html and fr.html, after book-seo.py and BEFORE prerender.py, so the
static mirror carries the new date. Idempotent. Fails if the component no longer has the expected
line (Design changed it): look at the new line rather than guessing. Values must not contain a quote.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "site-config.json"), encoding="utf-8"))["releaseDate"]
for v in d.values():
    if re.search(r"['\"\\<>]", v):
        sys.exit("set-release-date: a releaseDate value contains a quote, backslash or angle bracket")

LINE = re.compile(r"(this\.props\.releaseDate \|\| \(lang === 'fr' \? )'[^']*'( : )'[^']*'(\))")
for page in ("index.html", "fr.html"):
    s = open(page, encoding="utf-8").read()
    new, n = LINE.subn(lambda m: "%s'%s'%s'%s'%s" % (m.group(1), d["fr"], m.group(2), d["en"], m.group(3)), s)
    if n != 1:
        sys.exit("set-release-date: expected 1 releaseDate default in %s, found %d (Design changed it?)" % (page, n))
    open(page, "w", encoding="utf-8").write(new)
print("release date: %s / %s in index.html and fr.html" % (d["en"], d["fr"]))
