#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_chrome_copyright.py
# CONTRACT:v20260709b
# 대상: /var/www/f29-shared/f29-chrome.js
# 작업(설계 확정 스펙 그대로):
#   갭-1  COPYRIGHT[LANG] 4언어 상수 신설(DISCLAIMER 바로 아래)
#         + footerHTML에 f29-foot-copy div 1줄 + applyLang에 재렌더 1줄
#   갭-2  .f29-foot-dis 에 word-break:keep-all 추가 + .f29-foot-copy CSS 신설
#         (white-space:pre-line 로 COPYRIGHT 의 \n 3줄 렌더)
#   버전  CONTRACT:v20260709a -> v20260709b (마커 bump, 멱등 기준)
# 방식: 실측 리터럴 앵커 치환. 신규 CJK 문안 포함 → 이 스크립트는 반드시
#       GitHub 업로드 -> curl 경로로만 서버 반입(SSH 붙여넣기 절대 금지).
#       원자적 2단계 = 전 앵커 사전검증 통과해야만 쓰기. node --check 전파일.
# 사용: python3 patch_chrome_copyright.py --dry-run [경로]
#       python3 patch_chrome_copyright.py --apply   [경로]

import sys, os, subprocess, datetime, tempfile

TARGET = "/var/www/f29-shared/f29-chrome.js"
VER_OLD = "CONTRACT:v20260709a"
VER_NEW = "CONTRACT:v20260709b"

# --- 갭-1: COPYRIGHT 4언어 문안 (구 포털 COPY 승계 + en/zh/ja 신규) ----------
# 각 언어 3줄. 줄 사이는 리터럴 \n (JS 문자열 이스케이프) -> pre-line 이 렌더.
NL = "\\n"  # 파일에 backslash-n 2글자로 기록
CR = {
    "ko": NL.join([
        "Copyright \u00A9 2026 F29. All Rights Reserved.",
        "F29의 콘텐츠·UI·질문 구조·게이트 로직·디자인 및 소스코드는 저작권법의 보호를 받습니다.",
        "사전 서면 허가 없는 복제·배포·재게시·상업적 이용 및 유사 서비스 제작을 금지합니다. 위반 시 민·형사상 법적 조치를 취할 수 있습니다.",
    ]),
    "en": NL.join([
        "Copyright \u00A9 2026 F29. All Rights Reserved.",
        "F29's content, UI, question structures, gate logic, design, and source code are protected by copyright law.",
        "Reproduction, distribution, republication, commercial use, or creation of derivative services without prior written permission is prohibited and may result in civil and criminal action.",
    ]),
    "zh": NL.join([
        "Copyright \u00A9 2026 F29. All Rights Reserved.",
        "F29 的内容、UI、问题结构、门控逻辑、设计及源代码均受著作权法保护。",
        "未经事先书面许可，禁止复制、传播、转载、商业利用及制作类似服务。违者将依法追究民事及刑事责任。",
    ]),
    "ja": NL.join([
        "Copyright \u00A9 2026 F29. All Rights Reserved.",
        "F29 のコンテンツ・UI・質問構造・ゲートロジック・デザインおよびソースコードは著作権法により保護されています。",
        "事前の書面による許可なく複製・配布・再掲載・商業利用および類似サービスの作成を禁じます。違反した場合、民事・刑事上の法的措置を取ることがあります。",
    ]),
}
COPYRIGHT_BLOCK = (
    '  var COPYRIGHT={\n'
    '    ko:"' + CR["ko"] + '",\n'
    '    en:"' + CR["en"] + '",\n'
    '    zh:"' + CR["zh"] + '",\n'
    '    ja:"' + CR["ja"] + '"\n'
    '  };\n'
)

# --- 앵커/치환 정의 (실측 리터럴) ------------------------------------------
# A) COPYRIGHT 상수 삽입 + 버전마커 bump (DISCLAIMER 바로 아래 = CONTRACT 주석 앞)
A_OLD = "  // CONTRACT:v20260709a (B4 contact + B5 f29:lang)"
A_NEW = COPYRIGHT_BLOCK + "  // CONTRACT:v20260709b (B4 contact + B5 f29:lang + B6 copyright)"

# B) footerHTML: foot-dis div 다음에 foot-copy div 1줄 추가
B_OLD = "'<div class=\"f29-foot-dis\" id=\"f29-foot-dis\">'+DISCLAIMER[LANG]+'</div>'+"
B_NEW = B_OLD + "\n      '<div class=\"f29-foot-copy\" id=\"f29-foot-copy\">'+COPYRIGHT[LANG]+'</div>'+"

# C) applyLang: dis 재렌더 다음에 copy 재렌더 1줄 (동일 패턴, null-safe)
C_OLD = "if(dis) dis.textContent=DISCLAIMER[lang];"
C_NEW = C_OLD + "\n    var cp=document.getElementById(\"f29-foot-copy\"); if(cp) cp.textContent=COPYRIGHT[lang];"

# D) CSS: .f29-foot-dis 에 keep-all 추가 + .f29-foot-copy 신설
D_OLD = ".f29-foot-dis{margin-top:12px;font-size:.72rem;color:var(--txt3,#5A6B84);line-height:1.65;max-width:620px}"
D_NEW = (
    ".f29-foot-dis{margin-top:12px;font-size:.72rem;color:var(--txt3,#5A6B84);"
    "line-height:1.65;max-width:620px;word-break:keep-all;overflow-wrap:break-word}'+\n"
    "  '.f29-foot-copy{margin-top:10px;font-size:.66rem;color:var(--txt3,#5A6B84);"
    "line-height:1.6;max-width:620px;white-space:pre-line;word-break:keep-all;overflow-wrap:break-word}"
)


def die(msg):
    print("ABORT: " + msg)
    sys.exit(1)


def c(s, sub):
    return s.count(sub)


def node_check(content, label):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tf:
        tf.write(content); p = tf.name
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
    os.unlink(p)
    if r.returncode != 0:
        die("node --check failed (" + label + "):\n" + r.stderr)
    print("=== node --check %s: OK ===" % label)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    if mode not in ("--dry-run", "--apply"):
        die("usage: patch_chrome_copyright.py [--dry-run|--apply] [path]")
    path = sys.argv[2] if len(sys.argv) > 2 else TARGET
    if not os.path.exists(path):
        die("target not found: " + path)
    with open(path, "r", encoding="utf-8") as f:
        orig = f.read()

    # 0) 멱등
    if VER_NEW in orig:
        print("IDEMPOTENT: %s present, no change." % VER_NEW)
        for a in ["var COPYRIGHT", "f29-foot-copy", "keep-all", "white-space:pre-line"]:
            print("  grep %-22s = %d" % (a, c(orig, a)))
        sys.exit(0)

    # 1) 사전검증 (전부 통과해야 쓰기)
    print("=== PRE-VALIDATION ===")
    ok = True
    exact = {
        VER_OLD: 1, VER_NEW: 0,
        "var COPYRIGHT": 0, "f29-foot-copy": 0,
        A_OLD: 1, B_OLD: 1, C_OLD: 1, D_OLD: 1,
        "var DISCLAIMER={": 1,
    }
    for sub, exp in exact.items():
        got = c(orig, sub)
        good = got == exp
        ok = ok and good
        lbl = sub if len(sub) <= 34 else sub[:31] + "..."
        print("  [%s] count(%-34s)=%d expect=%d" % ("OK " if good else "!! ", lbl, got, exp))
    preserve = {
        "DISCLAIMER[LANG]": 1, "DISCLAIMER[lang]": 1,
        "CONTACT_LABEL": 2, "contactHTML": 2,
        'CustomEvent("f29:lang"': 1,
    }
    for sub, mn in preserve.items():
        got = c(orig, sub)
        good = got >= mn
        ok = ok and good
        print("  [%s] preserve(%-24s)=%d min=%d" % ("OK " if good else "!! ", sub, got, mn))
    if not ok:
        die("pre-validation failed -- no write.")

    # 2) 변환 (in-memory)
    new = orig
    new = new.replace(A_OLD, A_NEW, 1)
    new = new.replace(B_OLD, B_NEW, 1)
    new = new.replace(C_OLD, C_NEW, 1)
    new = new.replace(D_OLD, D_NEW, 1)

    # 3) 사후검증
    print("=== POST-VALIDATION ===")
    ok = True
    post = {
        VER_NEW: 1, VER_OLD: 0,
        "var COPYRIGHT": 1, "COPYRIGHT[LANG]": 1, "COPYRIGHT[lang]": 1,
        "f29-foot-copy": 4,          # CSS1 + footerHTML(class+id)2 + applyLang1
        "keep-all": 2,               # foot-dis + foot-copy
        "white-space:pre-line": 1,
    }
    for sub, exp in post.items():
        got = c(new, sub)
        good = got == exp
        ok = ok and good
        print("  [%s] count(%-22s)=%d expect=%d" % ("OK " if good else "!! ", sub, got, exp))
    for sub, mn in preserve.items():
        got = c(new, sub)
        good = got >= mn
        ok = ok and good
        print("  [%s] preserve(%-24s)=%d min=%d" % ("OK " if good else "!! ", sub, got, mn))
    # DISCLAIMER 4언어 원문 무손상 (블록 자체 불변)
    if "var DISCLAIMER={" not in new:
        ok = False; print("  [!! ] DISCLAIMER block lost")
    if not ok:
        die("post-validation failed -- no write.")

    # 4) node --check (치환본 전체)
    node_check(new, "patched (in-memory)")

    # 5) 바이트 증거
    ob, nb = len(orig.encode()), len(new.encode())
    print("=== BYTES: %d -> %d (delta %+d) ===" % (ob, nb, nb - ob))

    if mode == "--dry-run":
        print("=== DRY-RUN: no write. Review, then re-run --apply. ===")
        sys.exit(0)

    # 6) apply: 백업 -> 쓰기 -> 실파일 node --check + grep
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = path + ".bak_" + ts
    with open(bak, "w", encoding="utf-8") as f:
        f.write(orig)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print("=== WROTE %s (backup: %s) ===" % (path, bak))
    with open(path, "r", encoding="utf-8") as f:
        disk = f.read()
    node_check(disk, "on-disk file")
    print("=== ON-DISK GREP EVIDENCE ===")
    for a in ["CONTRACT:v20260709b", "CONTRACT:v20260709a", "var COPYRIGHT",
              "COPYRIGHT[LANG]", "COPYRIGHT[lang]", "f29-foot-copy",
              "keep-all", "white-space:pre-line",
              "var DISCLAIMER={", "DISCLAIMER[LANG]", "CONTACT_LABEL"]:
        print("  %-24s = %d" % (a, disk.count(a)))
    print("  final bytes = %d" % len(disk.encode()))


if __name__ == "__main__":
    main()
