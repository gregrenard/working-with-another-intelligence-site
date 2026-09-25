#!/usr/bin/env python3
"""Deploy-only transforms: clean URLs + static SEO head. Run from repo root,
AFTER the home-link ('./') transform, on every *.dc.html page + index.html, and
BEFORE renaming *.dc.html -> *.html. Idempotent.

1. Clean URLs  — strip the `.dc.html` extension from every internal link,
   canonical and og:url, so pages serve extensionless on GitHub Pages
   (e.g. /AI-Transformation). The files themselves are renamed *.dc.html ->
   *.html by the caller; GitHub Pages serves `X.html` at `/X`.
2. Static SEO  — copy each page's <helmet> tags into the real <head>, so
   crawlers and social / AI scrapers that don't execute JS still get title,
   description, canonical, og:/twitter: and JSON-LD (support.js also injects
   them at runtime; identical duplicates are harmless).
3. Static lang — add lang="en" to <html>.
"""
import re, glob

pages = sorted(glob.glob("*.dc.html")) + (["index.html"] if glob.glob("index.html") else [])
for p in pages:
    s = open(p, encoding="utf-8").read()

    # 1) clean URLs (links + canonical + og:url all lose the extension)
    s = s.replace(".dc.html", "")

    # 2) static lang (idempotent: '<html>' is absent once it's '<html lang=...>')
    s = s.replace("<html>", '<html lang="en">', 1)

    # 3) helmet -> head, only if head has no <title> yet (idempotent)
    head = s.split("<body", 1)[0]
    if "<title>" not in head:
        m = re.search(r"<helmet>(.*?)</helmet>", s, re.S)
        if m:
            inner = m.group(1).strip("\n")
            s = s.replace("</head>", inner + "\n</head>", 1)

    open(p, "w", encoding="utf-8").write(s)
    print("seo/clean-url:", p)
