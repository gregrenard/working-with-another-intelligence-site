#!/usr/bin/env python3
"""Deploy-only transform: SEO, languages and mobile head for the book site.

The book-site counterpart of gregory-renard-site's enrich-seo.py. Run from the repo
root, AFTER seo-clean-urls.py (the static <head> must already exist) and BEFORE
prerender.py. Idempotent: index.html is patched only once (marker), fr.html is
regenerated from index.html on every run.

1. Head extras (index): favicon, apple-touch-icon, theme-color (mobile browser bar).
2. JSON-LD Book: give both authors a url (equal weight, Marylène first), add the
   description, image and keywords.
3. Real French URL: hreflang fr -> /fr instead of /?lang=fr, and generate fr.html
   from index.html. fr.html has lang="fr", French <title>/description/OG/Twitter,
   og:locale fr_FR, canonical /fr, and the runtime defaults to French there. Non-JS
   crawlers then get a static French page (prerender.py mirrors it), not only English.
4. Language toggle: each language has its own URL. The FR/EN button navigates between
   / and /fr, a stored preference or a legacy ?lang=fr link on / goes to /fr, and
   ?lang=en on /fr goes to /.

The French strings are written here because the Design <helmet> only carries the
English ones. Keep them in line with promotion/00-positioning.md.
"""
import json
import re
import sys

SITE = "https://working-with-another-intelligence.com"
MARK = "<!--book-seo-->"

EN = {
    "title": "Working with Another Intelligence — An AI Reality Test and Management Reality Check",
    "desc": "A book by Marylène Delbourg-Delphis and Gregory Renard. Two years inside a European industrial group that made AI work for real, and what it changes for management.",
    "og_desc": "Two years inside a European industrial group that made AI work for real. By Marylène Delbourg-Delphis and Gregory Renard.",
    "tw_title": "Working with Another Intelligence",
    "tw_desc": "An AI Reality Test and Management Reality Check. By Marylène Delbourg-Delphis and Gregory Renard.",
}
FR = {
    "title": "Travailler avec une autre intelligence — L'IA à l'épreuve du réel, le management à l'épreuve de l'IA",
    "desc": "Le livre de Marylène Delbourg-Delphis et Gregory Renard : deux ans au cœur d'un grand groupe industriel européen qui a fait fonctionner l'IA pour de vrai, et ce que cela change pour le management. Ebook et livre audio.",
    "og_desc": "Deux ans au cœur d'un grand groupe industriel européen qui a fait fonctionner l'IA pour de vrai. Par Marylène Delbourg-Delphis et Gregory Renard.",
    "tw_title": "Travailler avec une autre intelligence",
    "tw_desc": "L'IA à l'épreuve du réel, le management à l'épreuve de l'IA. Par Marylène Delbourg-Delphis et Gregory Renard.",
}

HEAD_EXTRAS = (
    MARK + "\n"
    '<link rel="icon" type="image/png" sizes="256x256" href="assets/favicon.png">\n'
    '<link rel="icon" type="image/png" sizes="64x64" href="assets/favicon-64.png">\n'
    '<link rel="apple-touch-icon" sizes="180x180" href="assets/apple-touch-icon.png">\n'
    '<meta name="theme-color" content="#FAF7EF">\n'
)

# Runtime language logic, as exported by Design (must match exactly, or we stop).
MOUNT_DESIGN = """      const p = new URLSearchParams(location.search).get('lang');
      const l = p || localStorage.getItem('woai_lang');
      if (l === 'fr' || l === 'en') this.setState({ lang: l });
      document.documentElement.lang = l || 'en';"""
MOUNT_EN = """      const p = new URLSearchParams(location.search).get('lang');
      const l = p || localStorage.getItem('woai_lang');
      if (l === 'fr') { location.replace('/fr'); return; }
      document.documentElement.lang = 'en';"""
MOUNT_FR = """      const p = new URLSearchParams(location.search).get('lang');
      if (p === 'en') { location.replace('/'); return; }
      document.documentElement.lang = 'fr';"""
SETLANG_DESIGN = "    try { localStorage.setItem('woai_lang', l); document.documentElement.lang = l; } catch (e) {}\n    this.setState({ lang: l });"
SETLANG_NAV = "    try { localStorage.setItem('woai_lang', l); } catch (e) {}\n    if (l !== this.state.lang) location.href = (l === 'fr' ? '/fr' : '/');"


def must_replace(s, old, new, what, count=None):
    n = s.count(old)
    if n == 0 or (count is not None and n != count):
        sys.exit("book-seo: expected %s %s time(s), found %d — the Design page changed; update book-seo.py" % (what, count or ">=1", n))
    return s.replace(old, new)


def patch_jsonld(s):
    def fix(m):
        data = json.loads(m.group(1))
        if data.get("@type") != "Book":
            return m.group(0)
        for a in data.get("author", []):
            if a.get("name") == "Marylène Delbourg-Delphis":
                a.setdefault("url", "https://www.delbourg-delphis.org/")
                a.setdefault("sameAs", ["https://www.delbourg-delphis.org/"])
        data.setdefault("description", EN["desc"])
        data.setdefault("image", SITE + "/assets/og-cover.png")
        data.setdefault("keywords", "artificial intelligence, AI in the enterprise, management, cognitive sovereignty, System of Intelligence, AI governance, AI ROI")
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False) + "</script>"
    return re.sub(r'<script type="application/ld\+json">(.*?)</script>', fix, s, flags=re.S)


def main():
    s = open("index.html", encoding="utf-8").read()
    if MARK not in s:
        s = must_replace(s, "</head>", HEAD_EXTRAS + "</head>", "</head>", 1)
        s = patch_jsonld(s)
        s = must_replace(s, SITE + "/?lang=fr", SITE + "/fr", "hreflang ?lang=fr")
        s = must_replace(s, MOUNT_DESIGN, MOUNT_EN, "language mount logic", 1)
        s = must_replace(s, SETLANG_DESIGN, SETLANG_NAV, "setLang body", 1)
        open("index.html", "w", encoding="utf-8").write(s)
        print("book-seo: index.html patched (favicon, theme-color, JSON-LD, hreflang /fr, language routing)")
    else:
        print("book-seo: index.html already patched")

    f = s.replace(MOUNT_EN, MOUNT_FR)
    f = f.replace("state = { lang: 'en'", "state = { lang: 'fr'", 1)
    f = f.replace('<html lang="en">', '<html lang="fr">', 1)
    # Localize ONLY the static <head> and the <helmet> block (both HTML). Never the
    # component script: the English strings also live in JS string literals there,
    # and a French apostrophe ("L'IA") inside a '…' literal breaks the whole runtime.
    def localize(block):
        for k in ("title", "desc", "og_desc", "tw_title", "tw_desc"):
            block = block.replace(EN[k], FR[k])
        block = block.replace('<link rel="canonical" href="%s/">' % SITE, '<link rel="canonical" href="%s/fr">' % SITE)
        block = block.replace('<meta property="og:url" content="%s/">' % SITE, '<meta property="og:url" content="%s/fr">' % SITE)
        block = block.replace('<meta property="og:locale" content="en_US">', '<meta property="og:locale" content="__FR__">')
        block = block.replace('<meta property="og:locale:alternate" content="fr_FR">', '<meta property="og:locale:alternate" content="en_US">')
        return block.replace('<meta property="og:locale" content="__FR__">', '<meta property="og:locale" content="fr_FR">')
    head, body = f.split("<body", 1)
    body = re.sub(r"<helmet>.*?</helmet>", lambda m: localize(m.group(0)), body, count=1, flags=re.S)
    f = localize(head) + "<body" + body
    for need in ('<html lang="fr">', "state = { lang: 'fr'", FR["title"], SITE + '/fr">', "fr_FR"):
        if need not in f:
            sys.exit("book-seo: fr.html generation incomplete, missing %r" % need)
    open("fr.html", "w", encoding="utf-8").write(f)
    print("book-seo: fr.html generated (lang=fr, French head, canonical /fr)")


if __name__ == "__main__":
    main()
