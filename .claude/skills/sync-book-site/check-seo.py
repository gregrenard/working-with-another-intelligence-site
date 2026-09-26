#!/usr/bin/env python3
"""Gate (m): SEO + LLM-SEO + content-guardrail checks on the deployed files. No browser.

Per page (index.html = EN at /, fr.html = FR at /fr):
  - <title> and meta description present, sane length (WARN outside 30–70 / 70–170 chars);
  - Open Graph (title, description, image, url, locale) and Twitter card present;
  - og:image resolves to a local file of 1200 x 630;
  - JSON-LD parses; a Book with exactly two authors, Marylène Delbourg-Delphis first,
    each with a url;
  - favicon and apple-touch-icon referenced and present;
  - robots meta matches the mode in pages.json: noindex in draft, index after launch.
Site-wide:
  - robots.txt allows the AI / LLM crawlers (GPTBot, OAI-SearchBot, ClaudeBot,
    PerplexityBot, Google-Extended) and declares the sitemap;
  - llms.txt is well-formed (H1, > summary, ## Pages) and names both authors;
  - guardrail: the real client and the real people behind the book's first names never
    appear in any published file. Only SHA-256 prefixes are stored here, because this
    repository is public and a plain list would itself be the leak.

Usage (from the repo root):  python3 .claude/skills/sync-book-site/check-seo.py
Exit 1 on any BAD; WARN never fails.
"""
import hashlib
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest import DRAFT, SITE, prerender_files  # noqa: E402

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ClaudeBot", "PerplexityBot", "Google-Extended"]
FIRST_AUTHOR = "Marylène Delbourg-Delphis"
FORBIDDEN = {  # sha256(lowercased token)[:16]; see docstring
    "637d992f210633bc", "4abf4fecb1eea7ec", "b780fe6ad082ca51", "172cc579b2b6702b",
    "a4b6174b77106a94", "3e19e65ab4ac357b", "bac1183ce4e2db09", "1ef0c2c168980951",
    "edbf4bae814c4f7c", "e9f0bc5f473a8b51", "44cc2936d6add66c",
}
PUBLISHED = ["index.html", "fr.html", "404.html", "llms.txt", "robots.txt", "sitemap.xml", "README.md"]

bad = 0


def say(ok, msg, warn=False):
    global bad
    if ok:
        print("  ok: " + msg)
    elif warn:
        print("  WARN: " + msg)
    else:
        print("  BAD: " + msg)
        bad = 1


def meta(head, attr, name):
    m = re.search(r'<meta %s="%s" content="([^"]*)"' % (attr, re.escape(name)), head)
    return m.group(1) if m else None


def png_size(path):
    with open(path, "rb") as f:
        h = f.read(24)
    if h[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", h[16:24])


for page in prerender_files():
    if not os.path.exists(page):
        say(False, "%s missing" % page)
        continue
    s = open(page, encoding="utf-8").read()
    head = s.split("<body", 1)[0]
    t = re.search(r"<title>(.*?)</title>", head, re.S)
    title = t.group(1).strip() if t else ""
    desc = meta(head, "name", "description") or ""
    say(bool(title), "%s <title> present" % page)
    say(30 <= len(title) <= 70, "%s title length %d (30–70 recommended)" % (page, len(title)), warn=True)
    say(bool(desc), "%s meta description present" % page)
    say(70 <= len(desc) <= 170, "%s description length %d (70–170 recommended)" % (page, len(desc)), warn=True)
    for prop in ("og:title", "og:description", "og:image", "og:url", "og:locale"):
        say(meta(head, "property", prop) is not None, "%s %s" % (page, prop))
    say(meta(head, "name", "twitter:card") == "summary_large_image", "%s twitter:card summary_large_image" % page)
    img = meta(head, "property", "og:image") or ""
    local = img.split(SITE + "/", 1)[-1] if img.startswith(SITE) else ""
    if local and os.path.exists(local):
        size = png_size(local)
        say(size == (1200, 630), "%s og:image %s is %s (1200x630 expected)" % (page, local, size))
    else:
        say(False, "%s og:image does not resolve to a local file: %s" % (page, img))
    books = []
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', head, re.S):
        try:
            d = json.loads(block)
        except ValueError as e:
            say(False, "%s JSON-LD does not parse: %s" % (page, e))
            continue
        if d.get("@type") == "Book":
            books.append(d)
    if books:
        authors = books[0].get("author", [])
        say(len(authors) == 2 and authors[0].get("name") == FIRST_AUTHOR,
            "%s JSON-LD Book: 2 authors, %s first" % (page, FIRST_AUTHOR))
        say(all(a.get("url") for a in authors), "%s JSON-LD: every author has a url" % page)
    else:
        say(False, "%s JSON-LD Book missing from <head>" % page)
    for rel, f in (("icon", "assets/favicon.png"), ("apple-touch-icon", "assets/apple-touch-icon.png")):
        say(('rel="%s"' % rel) in head and os.path.exists(f), "%s %s referenced and present" % (page, rel))
    robots = meta(head, "name", "robots") or ""
    want = "noindex" if DRAFT else "index, follow"
    say(robots.startswith(want) or (not DRAFT and robots == "index, follow"),
        "%s robots meta '%s' matches mode (%s)" % (page, robots, "draft" if DRAFT else "launched"))

txt = open("robots.txt", encoding="utf-8").read()
for bot in AI_BOTS:
    say(re.search(r"User-agent: %s\s*\nAllow: /" % re.escape(bot), txt) is not None, "robots.txt allows %s" % bot)
say("Sitemap: %s/sitemap.xml" % SITE in txt, "robots.txt declares the sitemap")

llms = open("llms.txt", encoding="utf-8").read()
say(llms.startswith("# "), "llms.txt starts with an H1")
say(re.search(r"^> .{80,}", llms, re.M) is not None, "llms.txt has a > summary line")
say("## Pages" in llms, "llms.txt has a ## Pages section")
say(FIRST_AUTHOR in llms and "Gregory Renard" in llms, "llms.txt names both authors")

leaks = []
for f in PUBLISHED:
    if not os.path.exists(f):
        continue
    words = set(re.findall(r"[a-zà-ÿ]+", open(f, encoding="utf-8").read().lower()))
    hits = [w for w in words if hashlib.sha256(w.encode()).hexdigest()[:16] in FORBIDDEN]
    if hits:
        leaks.append("%s (%d forbidden token(s))" % (f, len(hits)))
say(not leaks, "guardrail: no real client or real surname in published files" + (": " + ", ".join(leaks) if leaks else ""))

print("  => SEO/LLM-SEO: %s" % ("FAIL" if bad else "pass"))
sys.exit(bad)
