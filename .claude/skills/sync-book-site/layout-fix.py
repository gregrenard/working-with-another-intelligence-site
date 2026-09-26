#!/usr/bin/env python3
"""Deploy-only CSS override: desktop + mobile layout fixes for the book page.

The book-site counterpart of gregory-renard-site's hero-wrap-fix.py. Claude Design
sets `white-space:nowrap` on the hero <h1> and on the big Oswald stat numbers. The
nowrap title then dictates the min-content width of its column, so on phones the
whole hero column overflows the viewport and body text is cut off on the right.
It also clips the (longer) French title even on a 1440 px desktop. Found on
2026-09-24 with headless screenshots at 390 px and 1440 px.

Fix, injected before </head> (`!important` beats the inline styles):
- hero <h1>: allow wrapping at every width, balanced lines (the English title still
  fits on one line per span on desktop, so its intended look is unchanged);
- stat numbers: allow wrapping and step the size down below 640 px;
- the hero eyebrow line and the authors/formats line may wrap below 640 px (Design
  gives the latter nowrap + ellipsis, which hid the formats on phones);
- a no-horizontal-scroll guard for narrow screens.
Run AFTER seo-clean-urls.py and BEFORE book-seo.py (fr.html inherits it). Idempotent.
"""
import sys

CSS = ('<style id="woai-layout-fix">'
       'h1[style*="nowrap"]{white-space:normal!important;text-wrap:balance}'
       '@media (max-width:640px){'
       'span[style*="tabular-nums"][style*="nowrap"]{white-space:normal!important;font-size:2rem!important;overflow-wrap:anywhere}'
       'p span[style*="nowrap"],p[style*="nowrap"]{white-space:normal!important;text-overflow:clip!important}'
       'html,body{overflow-x:hidden}'
       '}</style>')

s = open("index.html", encoding="utf-8").read()
if "woai-layout-fix" in s:
    print("layout-fix: already applied")
    sys.exit(0)
if "</head>" not in s:
    sys.exit("layout-fix: no </head> in index.html")
s = s.replace("</head>", CSS + "\n</head>", 1)
open("index.html", "w", encoding="utf-8").write(s)
print("layout-fix: index.html patched (hero wrap, stat numbers, no horizontal scroll)")
