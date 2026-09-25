#!/usr/bin/env python3
"""
pull-asset.py <project-relative-path> [session.jsonl]

Write a binary (or text) asset that was pulled via DesignSync get_file from the
session transcript to disk. Use when verify.sh flags an asset as MISSING because
it was changed/added in Claude Design (DesignSync get_file caps at 256 KiB, so
larger files still need a manual transfer).

    python3 .claude/skills/sync-site/pull-asset.py assets/greg-home-orange.jpg

Run from the repo root. Auto-discovers the most recent session transcript.
"""
import os, sys, json, glob, re, base64

REPO = os.getcwd()
if len(sys.argv) < 2:
    sys.exit("usage: pull-asset.py <assets/whatever.jpg> [session.jsonl]")
TARGET = sys.argv[1]


def find_jsonl():
    if len(sys.argv) > 2:
        return sys.argv[2]
    base = os.path.expanduser("~/.claude/projects/")
    enc = re.sub(r"[^A-Za-z0-9]", "-", REPO)
    cands = [os.path.join(base, enc)] + glob.glob(
        os.path.join(base, "*" + re.sub(r"[^A-Za-z0-9]", "-", os.path.basename(REPO))))
    js = []
    for d in dict.fromkeys(cands):
        if os.path.isdir(d):
            js += glob.glob(os.path.join(d, "*.jsonl"))
    js = sorted(set(js), key=os.path.getmtime)
    if not js:
        sys.exit("No session JSONL found.")
    return js[-1]


def extract_objs(text):
    out, i, key = [], 0, '{"method":"get_file"'
    while True:
        j = text.find(key, i)
        if j < 0:
            break
        depth, k, instr, esc, ok = 0, j, False, False, False
        while k < len(text):
            c = text[k]
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                instr = not instr
            elif not instr:
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        k += 1
                        ok = True
                        break
            k += 1
        if ok:
            try:
                o = json.loads(text[j:k])
                if o.get("method") == "get_file":
                    out.append(o)
            except Exception:
                pass
            i = k
        else:
            i = j + len(key)
    return out


def walk(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)


def main():
    jsonl = find_jsonl()
    best = None
    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            for s in walk(obj):
                if '"method":"get_file"' in s and TARGET in s:
                    for o in extract_objs(s):
                        if o.get("path") == TARGET and "content" in o:
                            best = o  # last occurrence wins
    if not best:
        sys.exit("Not found in transcript: " + TARGET)
    if best.get("truncated"):
        sys.exit("Asset is >256 KiB (truncated) — transfer it manually: " + TARGET)
    out = os.path.join(REPO, TARGET)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    if best.get("isBase64"):
        with open(out, "wb") as w:
            w.write(base64.b64decode(best["content"]))
    else:
        with open(out, "w", encoding="utf-8", newline="") as w:
            w.write(best["content"])
    print("WROTE %s  (%d bytes, isBase64=%s)" % (TARGET, os.path.getsize(out), best.get("isBase64")))


if __name__ == "__main__":
    main()
