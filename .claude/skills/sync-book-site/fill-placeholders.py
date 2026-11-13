#!/usr/bin/env python3
"""Deploy-only transform: fill the legal tokens Claude Design leaves in the page text.

The Design legal notice and privacy text contain {{HEBERGEUR}} and {{EMAIL_PRESSE}}, which a
visitor sees verbatim. The values live in site-config.json ("legal"). EMAIL_PRESSE also replaces
the component's default press address (the mailto behind "Press & talks"), which points at a
mailbox on the book's own domain that does not exist yet.

Run from the repo root on index.html and fr.html, after book-seo.py and BEFORE prerender.py, so the
static mirror carries the final text. Values are inserted into JS string literals: they must not
contain a quote or a backslash (checked). Idempotent. Fails if a token is left over.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
legal = json.load(open(os.path.join(HERE, "site-config.json"), encoding="utf-8"))["legal"]
for k, v in legal.items():
    if re.search(r"['\"\\<>]", v):
        sys.exit("fill-placeholders: value of %s contains a quote, backslash or angle bracket" % k)

OLD_PRESS = "presse@working-with-another-intelligence.com"
for page in ("index.html", "fr.html"):
    s = open(page, encoding="utf-8").read()
    for k, v in legal.items():
        s = s.replace("{{%s}}" % k, v)
    s = s.replace(OLD_PRESS, legal["EMAIL_PRESSE"])
    left = re.findall(r"\{\{[A-Z_]+\}\}", s)
    if left:
        sys.exit("fill-placeholders: %s still has %s, add them to site-config.json" % (page, sorted(set(left))))
    open(page, "w", encoding="utf-8").write(s)
print("legal: tokens filled in index.html and fr.html")
