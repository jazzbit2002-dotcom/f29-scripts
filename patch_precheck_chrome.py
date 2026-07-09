#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# PRECHECK-CHROME-MIGRATION  (v2.3 + DELTA 1-9)
# v2.3 fix: also strip standalone nav-doc CSS comments (e.g. Korean banner
# "/* ===== ... .portal-nav ... ===== */") that reference the removed component
# by name but aren't themselves prefixed rules -- caught by real-server dry-run.
# Migrates /var/www/f29/precheck/*/index.html into the shared f29-chrome contract.
# Read-first, dry-run-gated, atomic 7-file apply. HTML: NO node --check.
#
# Usage:
#   python3 patch_precheck_chrome.py --dry-run
#   python3 patch_precheck_chrome.py --apply
#
# --apply refuses unless ALL 7 files pass dry-run in the same run.

import sys, os, re, datetime

FILES = [
    "/var/www/f29/precheck/index.html",
    "/var/www/f29/precheck/checklist/index.html",
    "/var/www/f29/precheck/full/index.html",
    "/var/www/f29/precheck/position/index.html",
    "/var/www/f29/precheck/principles/index.html",
    "/var/www/f29/precheck/thesis/index.html",
    "/var/www/f29/precheck/valuation/index.html",
]

MARKER = "<!-- CONTRACT:v20260709b precheck-migration -->"
SCRIPT = '<script src="/shared/f29-chrome.js?v=20260709b" data-active="pb" defer></script>'
LISTENER = ('window.addEventListener("f29:lang",function(e){'
            'if(e&&e.detail&&e.detail.lang){setLang(e.detail.lang);}});')
SETLANG_ANCHOR = "window.setLang=function(l){applyHF(l);};"

# footer CSS prefixes (DELTA 8: report, non-fatal). Body ".disclaimer" is NOT here.
FOOT_CSS_PREFIXES = (".foot-in", ".foot-brand", ".foot-contact", ".foot-dis", ".foot-copy", "footer{")
NAV_CSS_PREFIX = ".portal-nav"
# v2.3: standalone documentation comments (e.g. a CJK banner like
# "/* ===== ... .portal-nav ... ===== */") reference the removed component by name
# but are not CSS rules themselves, so the prefix check above misses them. Match
# structurally: full single-line /* ... */ comment containing one of these ASCII
# terms (no CJK literal typed here -- we only match the ASCII substring embedded
# in whatever surrounding text the comment has).
NAV_COMMENT_TERMS = ("portal-nav", "navlinks", "nav-lang")

def c(text, pat):
    return text.count(pat)

class Abort(Exception):
    pass

def transform(path, text):
    """Return (new_text, report). Raises Abort on any fatal precondition."""
    rep = {"path": path, "before": {}, "after": {}, "foot_css_removed": [], "nav_comment_removed": [], "notes": []}
    is_index = path.endswith("/precheck/index.html")

    # ---------- BEFORE counts ----------
    b = rep["before"]
    for pat in ['f29-chrome.js', 'id="f29-header"', 'id="f29-footer"', MARKER,
                '<nav class="portal-nav">', '</nav>', '<nav class="nav">', '<footer>', '</footer>',
                SETLANG_ANCHOR, 'Copyright \u00a9', 'contactLabel', 'disclaimer:"F29',
                '<p class="disclaimer">', '\uad50\uc721\u00b7\uc790\uae30\uc810\uac80',
                'CTX_COPY', 'precheck_open', 'G-2GH6LTYB3R', 'URLSearchParams']:
        b[pat] = c(text, pat)

    # ---------- FATAL preconditions (abort whole run) ----------
    def need(pat, val):
        if b[pat] != val:
            raise Abort(f"{path}: precondition '{pat}' expected {val}, got {b[pat]}")
    need('f29-chrome.js', 0)
    need('id="f29-header"', 0)
    need('id="f29-footer"', 0)
    need(MARKER, 0)
    need('<nav class="portal-nav">', 1)
    # v2.2: sub-pages carry an internal step nav (<nav class="nav">...</nav>), so global
    # </nav> may be 2. We only remove the portal header nav (its opening tag is unique,
    # gated ==1 above) up to the NEAREST following </nav>. Body nav is preserved.
    # DELTA 9 intent kept: portal opener must be unique, and a closing </nav> must exist.
    if b['</nav>'] < 1:
        raise Abort(f"{path}: no </nav> found after portal-nav open")
    need('<footer>', 1)
    need('</footer>', 1)             # DELTA 9
    need(SETLANG_ANCHOR, 1)
    if b['Copyright \u00a9'] < 1:     # DELTA 7 before
        raise Abort(f"{path}: 'Copyright \u00a9' before expected >=1, got 0")
    if b['disclaimer:"F29'] != 4:     # HEADER_T footer keys, exact
        raise Abort(f"{path}: 'disclaimer:\"F29' before expected 4, got {b['disclaimer:\"F29']}")
    if b['contactLabel'] < 4:         # 4 keys + 1 usage = 5 normally; gate >=4, after==0 is authoritative
        raise Abort(f"{path}: 'contactLabel' before expected >=4, got {b['contactLabel']}")
    if is_index:
        for pat in ('precheck_open',):
            if b[pat] != 1:
                raise Abort(f"{path}: index '{pat}' before expected 1, got {b[pat]}")

    t = text

    # ---------- P1a: marker + chrome script before first </head> (exactly one insert) ----------
    if c(t, "</head>") < 1:
        raise Abort(f"{path}: no </head> found")
    t = t.replace("</head>", MARKER + "\n" + SCRIPT + "\n</head>", 1)

    # ---------- P2: remove <nav class="portal-nav"> ... </nav> -> f29-header ----------
    ns = t.index('<nav class="portal-nav">')
    ne = t.index('</nav>', ns) + len('</nav>')
    t = t[:ns] + '<div id="f29-header"></div>' + t[ne:]

    # ---------- P3: remove <footer> ... </footer> -> f29-footer ----------
    fs = t.index('<footer>')
    fe = t.index('</footer>', fs) + len('</footer>')
    t = t[:fs] + '<div id="f29-footer"></div>' + t[fe:]

    # ---------- P4 R1/R2: strip HEADER_T footer keys (regex, no CJK typing) ----------
    t, n_cl = re.subn(r',contactLabel:"[^"]*"', '', t)          # 4 expected
    t, n_dc = re.subn(r',\s*disclaimer:"[^"]*"', '', t)          # 4 expected
    rep["notes"].append(f"HEADER_T contactLabel keys removed={n_cl}; disclaimer keys removed={n_dc}")
    if n_cl != 4 or n_dc != 4:
        raise Abort(f"{path}: HEADER_T key removal off (contactLabel {n_cl}/4, disclaimer {n_dc}/4)")

    # ---------- P4 R3: drop footer disclaimer set() call ----------
    if 'set("disclaimer",t.disclaimer);' not in t:
        raise Abort(f"{path}: R3 anchor set(\"disclaimer\",...) not found")
    t = t.replace('set("disclaimer",t.disclaimer);', '')

    # ---------- P4 R4/R5 + CSS: line-based prefix removal ----------
    out_lines = []
    for line in t.split("\n"):
        s = line.strip()
        # R4 footContact
        if s == 'var _u="admin",_d="f29"+".io",fc=el("footContact");':
            continue
        if s.startswith('if(fc){fc.innerHTML=t.contactLabel'):
            continue
        # R5 footCopy / copyright
        if s.startswith('var cp=el("footCopy");'):
            continue
        if s.startswith('if(cp){cp.innerHTML="Copyright \u00a9'):
            continue
        # nav CSS
        if s.startswith(NAV_CSS_PREFIX):
            continue
        if s.startswith("@media") and ".portal-nav" in s:
            continue
        # v2.3: standalone comment lines documenting the removed nav component
        # (e.g. "/* ===== ... .portal-nav ... ===== */"). Structural match only:
        # full-line /* ... */ comment containing an ASCII nav term. Mandatory
        # removal (after-check hard-requires portal-nav/navlinks/nav-lang == 0).
        if s.startswith("/*") and s.endswith("*/") and any(term in s for term in NAV_COMMENT_TERMS):
            rep["nav_comment_removed"].append(s)
            continue
        # footer CSS (report, non-fatal)
        if any(s.startswith(p) for p in FOOT_CSS_PREFIXES):
            rep["foot_css_removed"].append(s)
            continue
        out_lines.append(line)
    t = "\n".join(out_lines)

    # ---------- P5: f29:lang listener after setLang def ----------
    if t.count(SETLANG_ANCHOR) != 1:
        raise Abort(f"{path}: P5 anchor count != 1")
    t = t.replace(SETLANG_ANCHOR, SETLANG_ANCHOR + "\n  " + LISTENER, 1)

    # ---------- AFTER counts ----------
    a = rep["after"]
    for pat in ['f29-chrome.js?v=20260709b', 'data-active="pb"', 'id="f29-header"',
                'id="f29-footer"', 'portal-nav', 'navlinks', '<nav class="nav">', '</nav>', '<footer>',
                'id="footContact"', 'id="footCopy"', 'id="disclaimer"',
                'Copyright \u00a9', 'contactLabel', 'disclaimer:"F29', 'f29:lang',
                MARKER, '<p class="disclaimer">', '\uad50\uc721\u00b7\uc790\uae30\uc810\uac80',
                'CTX_COPY', 'precheck_open', 'G-2GH6LTYB3R', 'URLSearchParams']:
        a[pat] = c(t, pat)

    # ---------- AFTER assertions ----------
    exact = {
        'f29-chrome.js?v=20260709b': 1, 'data-active="pb"': 1,
        'id="f29-header"': 1, 'id="f29-footer"': 1,
        'portal-nav': 0, 'navlinks': 0, '<footer>': 0,
        'id="footContact"': 0, 'id="footCopy"': 0, 'id="disclaimer"': 0,
        'Copyright \u00a9': 0, 'contactLabel': 0, 'disclaimer:"F29': 0,
        'f29:lang': 1, MARKER: 1,
    }
    for pat, val in exact.items():
        if a[pat] != val:
            raise Abort(f"{path}: AFTER '{pat}' expected {val}, got {a[pat]}")
    # v2.2 body-nav preservation: internal <nav class="nav"> untouched, and exactly the
    # ONE portal nav removed (total </nav> drops by precisely 1).
    if a['<nav class="nav">'] != b['<nav class="nav">']:
        raise Abort(f"{path}: body <nav class=\"nav\"> changed {b['<nav class=\"nav\">']}->{a['<nav class=\"nav\">']}")
    if a['</nav>'] != b['</nav>'] - 1:
        raise Abort(f"{path}: </nav> expected {b['</nav>']-1} after removing portal nav, got {a['</nav>']}")
    # body preservation invariants (DELTA 2)
    if a['<p class="disclaimer">'] != b['<p class="disclaimer">']:
        raise Abort(f"{path}: body <p class=\"disclaimer\"> changed {b['<p class=\"disclaimer\">']}->{a['<p class=\"disclaimer\">']}")
    if a['\uad50\uc721\u00b7\uc790\uae30\uc810\uac80'] != b['\uad50\uc721\u00b7\uc790\uae30\uc810\uac80']:
        raise Abort(f"{path}: body compliance copy changed")
    # index preservation (DELTA index)
    if is_index:
        for pat in ('CTX_COPY', 'precheck_open', 'G-2GH6LTYB3R', 'URLSearchParams'):
            if a[pat] != b[pat]:
                raise Abort(f"{path}: index preservation '{pat}' {b[pat]}->{a[pat]}")

    return t, rep


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("--dry-run", "--apply"):
        print("usage: patch_precheck_chrome.py [--dry-run|--apply]")
        sys.exit(2)

    results = []
    failed = False
    for path in FILES:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"[ABORT] missing file: {path}")
            failed = True
            break
        try:
            new_text, rep = transform(path, text)
            results.append((path, new_text, rep))
        except Abort as e:
            print(f"[ABORT] {e}")
            failed = True
            break

    if failed:
        print("\n=== RUN ABORTED. No file written. Re-inspect the reported file. ===")
        sys.exit(1)

    # report
    for path, _, rep in results:
        print(f"\n----- {path} -----")
        b, a = rep["before"], rep["after"]
        print(f"  before contactLabel={b['contactLabel']} disclaimer:\"F29={b['disclaimer:\"F29']} "
              f"Copyright={b['Copyright \u00a9']} portal_nav={b['<nav class=\"portal-nav\">']} "
              f"total_</nav>={b['</nav>']} body_nav={b['<nav class=\"nav\">']} </footer>={b['</footer>']}")
        print(f"  before_copyright={b['Copyright \u00a9']}  after_copyright={a['Copyright \u00a9']}")
        print(f"  after chrome={a['f29-chrome.js?v=20260709b']} pb={a['data-active=\"pb\"']} "
              f"hdr={a['id=\"f29-header\"']} ftr={a['id=\"f29-footer\"']} "
              f"portal-nav={a['portal-nav']} navlinks={a['navlinks']} footer={a['<footer>']} "
              f"f29:lang={a['f29:lang']} marker={a[MARKER]}")
        print(f"  after footContact={a['id=\"footContact\"']} footCopy={a['id=\"footCopy\"']} "
              f"id=disclaimer={a['id=\"disclaimer\"']} contactLabel={a['contactLabel']} "
              f"discKey={a['disclaimer:\"F29']}")
        print(f"  body p.disclaimer {b['<p class=\"disclaimer\">']}->{a['<p class=\"disclaimer\">']}  "
              f"edu-copy {b['\uad50\uc721\u00b7\uc790\uae30\uc810\uac80']}->{a['\uad50\uc721\u00b7\uc790\uae30\uc810\uac80']}")
        if path.endswith("/precheck/index.html"):
            print(f"  index preserve CTX_COPY={a['CTX_COPY']} precheck_open={a['precheck_open']} "
                  f"GA4={a['G-2GH6LTYB3R']} URLSearchParams={a['URLSearchParams']}")
        print(f"  nav-doc comments removed (mandatory, ASCII-term matched):")
        for l in rep["nav_comment_removed"]:
            print(f"      | {l}")
        print(f"  footer CSS lines removed (non-fatal, review):")
        for l in rep["foot_css_removed"]:
            print(f"      | {l}")
        print(f"  notes: {'; '.join(rep['notes'])}")

    print("\n=== ALL 7 FILES PASS DRY-RUN ===")

    if mode == "--apply":
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        for path, new_text, _ in results:
            bak = f"{path}.bak_chromemig_{ts}"
            with open(bak, "w", encoding="utf-8") as f:
                with open(path, encoding="utf-8") as src:
                    f.write(src.read())
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_text)
            print(f"[WROTE] {path}  (backup {bak})")
        print("\n=== APPLY COMPLETE: 7 files written. Run grep verification next. ===")


if __name__ == "__main__":
    main()
