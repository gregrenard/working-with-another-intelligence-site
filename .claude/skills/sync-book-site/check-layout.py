#!/usr/bin/env python3
"""Gate (l): desktop / tablet / mobile layout check, headless, no manual step.

For every pre-rendered page (index.html = EN at /, fr.html = FR at /fr) and every width
in WIDTHS, load the page inside an <iframe> of exactly that width and measure, after the
runtime has rendered:
  - horizontal scroll: documentElement.scrollWidth must equal clientWidth;
  - visible overflow: no element whose right edge passes the viewport unless an ancestor
    clips it (overflow hidden/clip), which is the case for ellipsis text;
  - the runtime rendered: #dc-root exists and has an <h1>;
  - no visible {{ }} placeholders (reported as WARN: they are content gaps in Design,
    already blocking gate (h), not layout bugs).

Why an iframe: headless Chrome cannot make a window narrower than 500 px, so a
`--window-size=390` screenshot is a 500 px layout cropped, which fakes an overflow
(found 2026-09-24). An iframe gives a true 390 px viewport.

The pages are served over loopback by a handler that injects the measuring script into
the HTML it serves (only for ?__layout=1), so nothing is written to the repo.

Usage (from the repo root):  python3 .claude/skills/sync-book-site/check-layout.py
Exit 1 if any page overflows at any width.
"""
import html
import os
import re
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from manifest import prerender_files  # noqa: E402

WIDTHS = [390, 768, 1440]
CHROME = os.environ.get("CHROME") or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
REPO = os.getcwd()

PROBE = r"""<script>
setTimeout(function () {
  var W = document.documentElement.clientWidth, SW = document.documentElement.scrollWidth, out = [];
  function clipped(e) {
    for (var a = e.parentElement; a && a !== document.body; a = a.parentElement) {
      var o = getComputedStyle(a).overflowX;
      if (o === 'hidden' || o === 'clip' || o === 'auto' || o === 'scroll') return true;
    }
    return false;
  }
  var root = document.getElementById('dc-root');
  (root ? root.querySelectorAll('*') : []).forEach(function (e) {
    if (e instanceof SVGElement) return;
    var r = e.getBoundingClientRect();
    if (r.width > 0 && r.right > W + 1 && !clipped(e))
      out.push(e.tagName + ' right=' + Math.round(r.right) + ' "' + (e.textContent || '').trim().slice(0, 50) + '"');
  });
  var h1 = root && root.querySelector('h1');
  var ph = ((root && root.innerText) || '').match(/\{\{[^}]*\}\}/g) || [];
  parent.postMessage(JSON.stringify({W: W, SW: SW, h1: !!h1, placeholders: ph.length, over: out.slice(0, 8)}), '*');
}, 6000);
</script>"""

HARNESS = """<!doctype html><html><body style="margin:0">
<iframe src="/{page}?__layout=1" style="width:{w}px;height:900px;border:0"></iframe>
<pre id="OUT"></pre>
<script>addEventListener('message', function (m) {{ document.getElementById('OUT').textContent = m.data; }});</script>
</body></html>"""


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/__harness":
            q = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
            body = HARNESS.format(page=q.get("page", "index.html"), w=int(q.get("w", "390"))).encode()
            return self._send(body)
        if "__layout=1" in query and path.endswith(".html"):
            f = os.path.join(REPO, path.lstrip("/"))
            if os.path.isfile(f):
                s = open(f, encoding="utf-8").read().replace("</body>", PROBE + "</body>", 1)
                return self._send(s.encode("utf-8"))
        if path.lower().endswith((".mp4", ".webm", ".mov", ".m4v", ".ogv")):
            return self.send_error(404, "media blocked during layout check")
        return super().do_GET()

    def _send(self, body):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def measure(port, page, w):
    url = "http://127.0.0.1:%d/__harness?page=%s&w=%d" % (port, page, w)
    try:
        dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--dump-dom",
                              "--window-size=%d,1000" % max(w + 40, 600),
                              "--virtual-time-budget=14000", url],
                             capture_output=True, text=True, timeout=60).stdout
    except Exception as e:  # noqa: BLE001
        return None, "render error: %s" % e
    m = re.search(r'<pre id="OUT">(.*?)</pre>', dom or "", re.S)
    if not m or not m.group(1).strip():
        return None, "no measurement (page did not render in time)"
    import json
    return json.loads(html.unescape(m.group(1))), None


def main():
    if not os.path.exists(CHROME):
        print("  WARN: Chrome not found, layout check skipped")
        return 0
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=REPO))
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    bad = 0
    try:
        for page in prerender_files():
            if not os.path.exists(page):
                continue
            for w in WIDTHS:
                r, err = measure(port, page, w)
                label = "%s @%dpx" % (page, w)
                if err:
                    print("  BAD: %s: %s" % (label, err)); bad = 1; continue
                if r["W"] != w:
                    print("  BAD: %s: viewport is %d px, not %d" % (label, r["W"], w)); bad = 1; continue
                problems = []
                if r["SW"] > r["W"]:
                    problems.append("horizontal scroll (scrollWidth %d > %d)" % (r["SW"], r["W"]))
                if r["over"]:
                    problems.append("%d element(s) past the right edge: %s" % (len(r["over"]), "; ".join(r["over"][:3])))
                if not r["h1"]:
                    problems.append("runtime did not render an <h1>")
                if problems:
                    print("  BAD: %s: %s" % (label, " | ".join(problems))); bad = 1
                else:
                    print("  ok: %s (no overflow)" % label)
                if r["placeholders"]:
                    print("  WARN: %s shows %d {{ }} placeholder(s) — fill them in Claude Design" % (label, r["placeholders"]))
    finally:
        httpd.shutdown()
        httpd.server_close()
    return bad


if __name__ == "__main__":
    sys.exit(main())
