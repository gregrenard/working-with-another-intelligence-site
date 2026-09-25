#!/usr/bin/env python3
"""
extract-pulled.py — write the Claude Design pages listed in pages.json to disk, byte-exact.

Reads the current session transcript (JSONL) and reconstructs each page from the
DesignSync get_file results — handling BOTH inline results and large results that
were persisted to a tool-results/<toolu>.txt file. Keeps the freshest pull per
path (last occurrence wins). No hand-retyping = no corruption risk on a live site.

Usage:
    python3 .claude/skills/sync-site/extract-pulled.py [path/to/session.jsonl]

If no transcript is given, auto-discovers the most recently modified *.jsonl under
~/.claude/projects/<cwd-encoded>/ (= the current session). Run from the repo root.
"""
import os, sys, json, glob, re

from manifest import design_pages  # single source of truth: pages.json

REPO = os.getcwd()
PAGES = design_pages()


def find_jsonl():
    if len(sys.argv) > 1:
        return sys.argv[1]
    base = os.path.expanduser("~/.claude/projects/")
    # Claude Code encodes the project dir by replacing every non-alphanumeric char with '-'
    enc = re.sub(r"[^A-Za-z0-9]", "-", REPO)
    candidates = [os.path.join(base, enc)]
    # Fallback: any project dir ending with the repo basename
    candidates += glob.glob(os.path.join(base, "*" + re.sub(r"[^A-Za-z0-9]", "-", os.path.basename(REPO))))
    seen = set()
    js = []
    for d in candidates:
        if d in seen or not os.path.isdir(d):
            continue
        seen.add(d)
        js += glob.glob(os.path.join(d, "*.jsonl"))
    js = sorted(set(js), key=os.path.getmtime)
    if not js:
        sys.exit("No session JSONL found (looked under: %s)" % ", ".join(candidates))
    return js[-1]


def extract_objs(text):
    """Yield (path, content) for every COMPLETE {"method":"get_file"...} object in text.
    String-aware balanced-brace scan, so truncated previews are skipped (not partial-matched)."""
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
                if o.get("method") == "get_file" and "content" in o:
                    out.append((o["path"], o["content"]))
            except Exception:
                pass
            i = k
        else:
            i = j + len(key)  # truncated/persisted preview — skip
    return out


def walk_strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from walk_strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_strings(v)


def main():
    jsonl = find_jsonl()
    print("Transcript:", jsonl)
    records, order = {}, [0]  # path -> (order, kind, payload)

    def consider(p, kind, payload):
        records[p] = (order[0], kind, payload)
        order[0] += 1

    with open(jsonl, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            for s in walk_strings(obj):
                if "Full output saved to:" in s and '"method":"get_file"' in s:
                    m = re.search(r"Full output saved to:\s*(\S+\.txt)", s)
                    pm = re.search(r'"path":"((?:[^"\\]|\\.)*)"', s)
                    if m and pm:
                        try:
                            p = json.loads('"' + pm.group(1) + '"')
                        except Exception:
                            p = pm.group(1)
                        consider(p, "file", m.group(1))
                elif '"method":"get_file"' in s:
                    for (p, c) in extract_objs(s):
                        consider(p, "inline", c)

    wrote, missing = 0, []
    for p in PAGES:
        if p not in records:
            missing.append(p)
            continue
        _, kind, payload = records[p]
        if kind == "inline":
            content = payload
        else:
            try:
                txt = open(payload, encoding="utf-8").read()
            except Exception as e:
                missing.append("%s (txt unreadable: %s)" % (p, e))
                continue
            objs = extract_objs(txt)
            content = next((c for (pp, c) in objs if pp == p),
                           objs[0][1] if objs else None)
            if content is None:
                missing.append("%s (no content in txt)" % p)
                continue
        with open(os.path.join(REPO, p), "w", encoding="utf-8", newline="") as out:
            out.write(content)
        wrote += 1
        print("WROTE  %-32s %7d bytes  (%s)" % (p, len(content), kind))

    print("\n%d/%d pages written." % (wrote, len(PAGES)))
    if missing:
        print("MISSING:", missing)
        sys.exit(1)


if __name__ == "__main__":
    main()
