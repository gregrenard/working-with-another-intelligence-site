#!/usr/bin/env python3
"""Deploy-only transform: wire the three book-page forms to the Google Sheet endpoint.

Claude Design's forms show a success state and send nothing. Rather than patching the component
script (a stray apostrophe in a JS string once broke the runtime), this builds assets/forms.js
from forms-overlay.js + site-config.json and adds one <script> tag to the static <head> of
index.html and fr.html.

Run from the repo root AFTER book-seo.py (fr.html must exist, and the head is final once
seo-clean-urls.py has run) and BEFORE prerender.py. Idempotent.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "site-config.json"), encoding="utf-8"))
endpoint = cfg.get("formEndpoint", "")
if not endpoint.startswith("https://script.google.com/macros/s/") or not endpoint.endswith("/exec"):
    sys.exit("patch-forms: formEndpoint in site-config.json is not an Apps Script /exec URL")

overlay = open(os.path.join(HERE, "forms-overlay.js"), encoding="utf-8").read()
os.makedirs("assets", exist_ok=True)
with open("assets/forms.js", "w", encoding="utf-8") as f:
    f.write("window.BOOK_FORMS=" + json.dumps({"formEndpoint": endpoint}) + ";\n" + overlay)

TAG = '<script src="assets/forms.js" defer></script>\n'
ANCHOR = '<script src="./support.js"></script>\n'
for page in ("index.html", "fr.html"):
    s = open(page, encoding="utf-8").read()
    if TAG in s:
        continue
    if ANCHOR not in s:
        sys.exit("patch-forms: support.js anchor not found in %s, re-inspect the head" % page)
    open(page, "w", encoding="utf-8").write(s.replace(ANCHOR, ANCHOR + TAG, 1))
print("forms: assets/forms.js written, script tag present in index.html and fr.html")
