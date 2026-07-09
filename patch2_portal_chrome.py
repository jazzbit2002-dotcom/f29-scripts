#!/usr/bin/env python3
# patch2_portal_chrome.py
# PATCH:f29-portal-chrome:v2.0
# 대상: /var/www/f29-portal/index.html
# 작업: 포털 자체 <nav> / <footer> 제거 -> chrome.js 배선(head script,
#       #f29-header, #f29-footer) + f29:lang 수신 리스너 삽입.
# 방식: 실측 ASCII 앵커 기반 extract-and-replace. 스크립트 소스에 CJK 리터럴
#       무접촉(nav 블록의 中/日, footer의 한글 COPY는 런타임 추출로만 다룸).
#       원자적 2단계 = 사전검증 전부 통과해야만 쓰기. 멱등(마커 판정).
# 사용: python3 patch2_portal_chrome.py --dry-run [경로]
#       python3 patch2_portal_chrome.py --apply   [경로]

import sys, os, subprocess, datetime, tempfile

TARGET = "/var/www/f29-portal/index.html"
MARKER = "PATCH:f29-portal-chrome:v2.0"

HEAD_SCRIPT = ('<!-- ' + MARKER + ' --><script src="/shared/f29-chrome.js?v=20260709a" '
               'data-active="" defer></script>\n')
HEADER_MOUNT = '<!-- ' + MARKER + ' header --><div id="f29-header"></div>'
FOOTER_MOUNT = '<!-- ' + MARKER + ' footer --><div id="f29-footer"></div>'
LISTENER = (
    '<!-- ' + MARKER + ' lang START -->\n'
    '<script>\n'
    'window.addEventListener("f29:lang", function(e){\n'
    '  if(e && e.detail && e.detail.lang){ setLang(e.detail.lang); }\n'
    '});\n'
    '</script>\n'
    '<!-- ' + MARKER + ' lang END -->\n'
)

def die(msg):
    print("ABORT: " + msg)
    sys.exit(1)

def c(s, sub):
    return s.count(sub)

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    if mode not in ("--dry-run", "--apply"):
        die("usage: patch2_portal_chrome.py [--dry-run|--apply] [path]")
    path = sys.argv[2] if len(sys.argv) > 2 else TARGET
    if not os.path.exists(path):
        die("target not found: " + path)
    with open(path, "r", encoding="utf-8") as f:
        orig = f.read()

    # 0) 멱등 판정
    if MARKER in orig:
        print("IDEMPOTENT: marker present, no change. (" + MARKER + ")")
        for a in ["f29-chrome.js", 'id="f29-header"', 'id="f29-footer"', "f29:lang"]:
            print("  grep %-18s = %d" % (a, c(orig, a)))
        sys.exit(0)

    # 1) 사전검증 (전부 통과해야 쓰기) --------------------------------------
    print("=== PRE-VALIDATION ===")
    ok = True
    exact = {
        "<nav>": 1, "</nav>": 1, "<footer>": 1, "</footer>": 1,
        "</head>": 1, "</body>": 1,
        "f29-chrome.js": 0, 'id="f29-header"': 0, 'id="f29-footer"': 0,
    }
    for sub, exp in exact.items():
        got = c(orig, sub)
        good = got == exp
        ok = ok and good
        print("  [%s] count(%-16s)=%d expect=%d" % ("OK " if good else "!! ", sub, got, exp))
    preserve = {
        "naver-site-verification": 1, "G-2GH6LTYB3R": 2,
        "function setLang": 1, "PATCH:f29-portal-search:v1.1": 2, "heroTitle": 1,
    }
    for sub, mn in preserve.items():
        got = c(orig, sub)
        good = got >= mn
        ok = ok and good
        print("  [%s] preserve(%-28s)=%d min=%d" % ("OK " if good else "!! ", sub, got, mn))
    if c(orig, "<nav>") == 1 and c(orig, "</nav>") == 1 and orig.index("<nav>") >= orig.index("</nav>"):
        ok = False; print("  [!! ] nav order")
    if c(orig, "<footer>") == 1 and c(orig, "</footer>") == 1 and orig.index("<footer>") >= orig.index("</footer>"):
        ok = False; print("  [!! ] footer order")
    if not ok:
        die("pre-validation failed -- no write.")

    # 2) 변환 (in-memory, ASCII 앵커 extract-and-replace) --------------------
    nav_block = orig[orig.index("<nav>"): orig.index("</nav>") + len("</nav>")]
    foot_block = orig[orig.index("<footer>"): orig.index("</footer>") + len("</footer>")]
    new = orig
    new = new.replace(nav_block, HEADER_MOUNT, 1)
    new = new.replace(foot_block, FOOTER_MOUNT, 1)
    new = new.replace("</head>", HEAD_SCRIPT + "</head>", 1)
    new = new.replace("</body>", LISTENER + "</body>", 1)

    # 3) 사후검증 (in-memory) ----------------------------------------------
    print("=== POST-VALIDATION ===")
    ok = True
    post = {
        "f29-chrome.js": 1, 'id="f29-header"': 1, 'id="f29-footer"': 1,
        "f29:lang": 1, MARKER: 5,
        "<nav>": 0, "</nav>": 0, "<footer>": 0, "</footer>": 0,
    }
    for sub, exp in post.items():
        got = c(new, sub)
        good = got == exp
        ok = ok and good
        print("  [%s] count(%-16s)=%d expect=%d" % ("OK " if good else "!! ", sub, got, exp))
    for sub, mn in preserve.items():
        got = c(new, sub)
        good = got >= mn
        ok = ok and good
        print("  [%s] preserve(%-28s)=%d min=%d" % ("OK " if good else "!! ", sub, got, mn))
    if not ok:
        die("post-validation failed -- no write.")

    # 4) node --check (신규 리스너 JS만 추출) -------------------------------
    js = LISTENER.split("<script>\n", 1)[1].split("\n</script>", 1)[0]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(js); jspath = tf.name
    r = subprocess.run(["node", "--check", jspath], capture_output=True, text=True)
    os.unlink(jspath)
    if r.returncode != 0:
        die("node --check failed:\n" + r.stderr)
    print("=== node --check listener JS: OK ===")

    # 5) 바이트 증거 (기능 검증 아님, 힌트) --------------------------------
    ob, nb = len(orig.encode()), len(new.encode())
    print("=== BYTES: %d -> %d (delta %+d) ===" % (ob, nb, nb - ob))
    print("  removed nav bytes    : %d" % len(nav_block.encode()))
    print("  removed footer bytes : %d" % len(foot_block.encode()))

    if mode == "--dry-run":
        print("=== DRY-RUN: no write. Review, then re-run --apply. ===")
        sys.exit(0)

    # 6) apply: 백업 -> 쓰기 -> 실파일 재판독 grep --------------------------
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = path + ".bak_" + ts
    with open(bak, "w", encoding="utf-8") as f:
        f.write(orig)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print("=== WROTE %s (backup: %s) ===" % (path, bak))
    with open(path, "r", encoding="utf-8") as f:
        disk = f.read()
    print("=== ON-DISK GREP EVIDENCE ===")
    for a in ["f29-chrome.js?v=20260709a", 'id="f29-header"', 'id="f29-footer"',
              "f29:lang", "naver-site-verification", "G-2GH6LTYB3R",
              "function setLang", "PATCH:f29-portal-search:v1.1",
              "<nav>", "<footer>"]:
        print("  %-30s = %d" % (a, disk.count(a)))
    print("  final bytes = %d" % len(disk.encode()))

if __name__ == "__main__":
    main()
