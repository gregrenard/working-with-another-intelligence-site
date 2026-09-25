#!/usr/bin/env python3
"""Deploy-only transform: static pre-render so non-JS consumers see real content.

The dc-runtime (support.js) renders the page BODY from a {{ }} template at runtime
(React, loaded from unpkg). So the raw HTML body ships unresolved {{ }} bindings —
fine for browsers and for Google (it executes JS), but bad for no-JS browsers and
non-JS crawlers (LinkedIn body scrape, many AI crawlers), and it "looks broken" in
a no-JS view.

Fix (progressive enhancement, no cloaking, no JS-timing): headless-render each page
with Chrome, capture the resolved #dc-root HTML, and inject it as a *visible-by-default*
mirror that the runtime hides the instant it mounts — via pure CSS:

    x-dc{display:none}                              /* hide the raw {{ }} template   */
    #dc-root:not(:empty) ~ #dc-prerender{display:none}  /* hide mirror once React mounts */

- no-JS / pre-JS / React-fails-to-load : <x-dc> hidden, #dc-prerender shows real content
- JS ok : runtime replaces <x-dc> with a populated #dc-root -> CSS hides the mirror
The <x-dc> template is KEPT (runtime needs it for the FR/EN toggle + the form), so
raw view-source still contains {{ }} — what changes is what *renders* and what non-JS
crawlers *extract*.

MUST run LAST (on the final *.html, after clean-URLs + rename) so the mirror's links
are extensionless. Non-fatal: if Chrome is missing it warns and skips (pages still
render via JS). Idempotent: strips any prior injection before re-injecting.

Usage:  python3 .claude/skills/sync-site/prerender.py   (from repo root)
"""
import os, re, sys, time, subprocess, threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO = os.getcwd()
# 8 full content pages (skip the 3 redirect stubs: AI-Lab/AI-Transformation/Advisory-Execution)
from manifest import prerender_files  # single source of truth: pages.json

PAGES = prerender_files()

CHROME = os.environ.get("CHROME") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SWAP_CSS = "x-dc{display:none}#dc-root:not(:empty)~#dc-prerender{display:none}"
STYLE = '<style id="dc-prerender-css">' + SWAP_CSS + "</style>"
MARK_A, MARK_B = "<!--dc-prerender-start-->", "<!--dc-prerender-end-->"
MEDIA_EXT = (".mp4", ".webm", ".mov", ".m4v", ".ogv")


class Handler(SimpleHTTPRequestHandler):
    """Serve the repo over loopback, but refuse heavy media.

    Chrome's --virtual-time-budget does not advance while a media element is
    still loading, so <video preload="metadata"> pointing at the 18 MB
    assets/redefining-work-ai.mp4 (Essays + Method) stalled the render past the
    45 s timeout — Essays failed on five consecutive syncs and then began
    failing standalone too. What we capture is the resolved DOM, and the
    <video> markup is byte-identical whether or not its metadata loaded, so
    404-ing the file costs nothing and makes every render deterministic.
    """

    def send_head(self):
        if self.path.split("?")[0].lower().endswith(MEDIA_EXT):
            self.send_error(404, "media blocked during pre-render")
            return None
        return super().send_head()

    def log_message(self, *args):
        pass


def render(url):
    """Headless-render url, return full post-JS DOM HTML (or None on failure).
    Minimal flags — matches the validated spike; extra flags (user-data-dir / sandbox)
    made Chrome hang."""
    try:
        out = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--dump-dom",
             "--virtual-time-budget=9000", url],
            capture_output=True, text=True, timeout=45)
        return out.stdout or None
    except Exception as e:
        print("  render error:", e)
        return None


_TOK = re.compile(r"<div\b|</div\s*>", re.I)


def extract_dc_root_inner(html):
    """Return inner HTML of <div id="dc-root">…</div> via balanced <div> scan."""
    m = re.search(r'<div\b[^>]*\bid="dc-root"[^>]*>', html)
    if not m:
        return None
    start = m.end()
    depth, pos = 1, start
    for t in _TOK.finditer(html, start):
        if t.group().lower().startswith("<div"):
            depth += 1
        else:
            depth -= 1
            if depth == 0:
                return html[start:t.start()]
        pos = t.end()
    return None


def strip_prior(s):
    """Remove a previous mirror AND the newline each injection added, so a page
    does not accumulate two blank lines on every sync (it did until 2026-08-30)."""
    s = re.sub(r'\n?<style id="dc-prerender-css">.*?</style>', "", s, flags=re.S)
    s = re.sub(re.escape(MARK_A) + ".*?" + re.escape(MARK_B) + r"\n?", "", s, flags=re.S)
    return s


def main():
    if not os.path.exists(CHROME):
        print("WARN: Chrome not found at %r — skipping pre-render (pages still render via JS)." % CHROME)
        return 0

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=REPO))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    done, skipped = 0, []
    try:
        for page in PAGES:
            if not os.path.exists(page):
                continue
            url = "http://127.0.0.1:%d/%s" % (port, "" if page == "index.html" else page)
            dom = render(url)
            if not dom:
                skipped.append(page + " (no render)"); continue
            inner = extract_dc_root_inner(dom)
            if inner is None:
                skipped.append(page + " (no #dc-root)"); continue
            ph = len(re.findall(r"\{\{[^}]*\}\}", inner))
            if ph:
                skipped.append("%s (%d placeholders left)" % (page, ph)); continue
            if "</x-dc>" in inner:
                skipped.append(page + " (contains </x-dc>)"); continue

            s = open(page, encoding="utf-8").read()
            s = strip_prior(s)
            if "</x-dc>" not in s or "</head>" not in s:
                skipped.append(page + " (no </x-dc> or </head> anchor)"); continue
            s = s.replace("</head>", STYLE + "\n</head>", 1)
            block = MARK_A + '<div id="dc-prerender">' + inner + "</div>" + MARK_B
            s = s.replace("</x-dc>", "</x-dc>\n" + block, 1)
            open(page, "w", encoding="utf-8").write(s)
            done += 1
            print("prerender: %-22s (+%d bytes mirror, 0 placeholders)" % (page, len(inner)))
    finally:
        httpd.shutdown()
        httpd.server_close()

    print("\nprerendered %d/%d pages." % (done, len(PAGES)))
    if skipped:
        print("SKIPPED:", skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
