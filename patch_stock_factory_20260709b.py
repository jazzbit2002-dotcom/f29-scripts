#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch_stock_factory_20260709b.py
# STOCK-FACTORY-CONTRACT-SYNC: v20260708c -> v20260709b (안 B)
# 대상: /root/krx-moneyflow/build_stock_pages.py  (생성기. 산출물 306개 직접 수정 아님)
# 작업(설계 확정 스펙 그대로):
#   P1  버전 bump: chrome.js?v=20260708c -> v=20260709b (244행, 파일 내 유일)
#   P2  안 B 상단: .judg 카드에 종목 특화 컴플라이언스 문구 span 삽입 (275행)
#       "특정 종목의 매수·매도 추천이 아닙니다." — footer 아닌 본문 보존
#   P3  안 B 하단: 자체 footer성 .disc 단락 제거 (278-279행)
#       — disclaimer/copyright/contact 는 chrome.js footer SSOT 로 위임
#   P4  CSS: .judg-disc 규칙 신설 (.disc 정의 옆). f-string 이스케이프 {{ }} 준수
#   (nav 하드코딩 277행은 이번 패치 범위 — P5 로 함께 제거)
#   P5  자체 <nav class="navlinks"> 제거 (chrome.js #f29-header 가 NAV6 주입 → 중복 방지)
#       .navlinks CSS(266-267행)는 무해하게 존치(서버-정본 diff 최소화, 롤백사고 방지 원칙)
# 방식: 실측 리터럴 앵커 치환. 신규 CJK 문안 포함 → GitHub 업로드->curl 로만 반입.
#       SSH 붙여넣기 절대 금지. 원자적 2단계 = 전 앵커 사전검증 통과해야만 쓰기.
#       py_compile 문법검사(치환본/실파일 이중).
# 사용: python3 patch_stock_factory_20260709b.py --dry-run [경로]
#       python3 patch_stock_factory_20260709b.py --apply   [경로]

import sys, os, subprocess, datetime, tempfile

TARGET = "/root/krx-moneyflow/build_stock_pages.py"

# --- 앵커/치환 정의 (실측 리터럴 — B1~B5 출력 기준) ------------------------

# P1) 버전 bump (244행, 파일 내 유일 — grep -c=1 실측)
P1_OLD = '<script src="/shared/f29-chrome.js?v=20260708c" data-active="" defer></script>'
P1_NEW = '<script src="/shared/f29-chrome.js?v=20260709b" data-active="" defer></script>'

# P2) .judg 카드에 종목 특화 컴플라이언스 span 삽입 (275행)
#     f-string 내부이므로 {line1} 변수 보존. CJK 고정문안 + span 은 리터럴.
P2_OLD = '<div class="judg">{line1}</div>'
P2_NEW = ('<div class="judg">{line1}'
          '<span class="judg-disc">특정 종목의 매수·매도 추천이 아닙니다.</span></div>')

# P3) 자체 footer성 .disc 단락 제거 (278-279행, 2줄 통짜)
#     f-string 내부 고정 텍스트(변수 없음) — 통째 삭제.
P3_OLD = ('<p class="disc">본 페이지는 거래대금 기반 참고지표이며 특정 종목의 매수·매도 추천이 아닙니다.\n'
          '투자 판단과 책임은 이용자 본인에게 있습니다. \u00A9 F29 \u00B7 f29.io</p>\n')
P3_NEW = ''

# P4) CSS: .judg-disc 신설 (.disc 정의 라인 앞에 삽입). f-string 이스케이프 {{ }} 준수.
P4_OLD = '.disc{{color:#6b7280;font-size:.75rem;margin-bottom:24px}}'
P4_NEW = ('.judg-disc{{display:block;margin-top:6px;color:#6b7280;font-size:.72rem}}\n'
          '.disc{{color:#6b7280;font-size:.75rem;margin-bottom:24px}}')

# P5) 자체 nav 제거 (277행). chrome.js #f29-header 가 NAV6 주입하므로 중복.
P5_OLD = '<nav class="navlinks">{nav_links}</nav>\n'
P5_NEW = ''

PATCHES = [
    ("P1_version_bump", P1_OLD, P1_NEW, 1),
    ("P2_judg_disc_span", P2_OLD, P2_NEW, 1),
    ("P3_remove_disc",   P3_OLD, P3_NEW, 1),
    ("P4_css_judg_disc", P4_OLD, P4_NEW, 1),
    ("P5_remove_nav",    P5_OLD, P5_NEW, 1),
]


def die(msg):
    print("ABORT: " + msg)
    sys.exit(1)


def c(s, sub):
    return s.count(sub)


def py_check(content, label):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(content); p = tf.name
    r = subprocess.run([sys.executable, "-m", "py_compile", p],
                       capture_output=True, text=True)
    os.unlink(p)
    # py_compile 은 .pyc 를 남길 수 있으나 tmp 라 무해
    if r.returncode != 0:
        die("py_compile failed (" + label + "):\n" + r.stderr)
    print("=== py_compile %s: OK ===" % label)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    if mode not in ("--dry-run", "--apply"):
        die("usage: patch_stock_factory_20260709b.py [--dry-run|--apply] [path]")
    path = sys.argv[2] if len(sys.argv) > 2 else TARGET
    if not os.path.exists(path):
        die("target not found: " + path)
    with open(path, "r", encoding="utf-8") as f:
        orig = f.read()

    # 0) 멱등 — 이미 적용됐으면 종료
    if "20260709b" in orig and "judg-disc" in orig:
        print("IDEMPOTENT: v20260709b + judg-disc present, no change.")
        for a in ["20260708c", "20260709b", "judg-disc",
                  'class="disc"', 'class="navlinks">{nav_links}']:
            print("  grep %-28s = %d" % (a, c(orig, a)))
        sys.exit(0)

    # 1) 사전검증 — 전 앵커 정확히 1회 (전부 통과해야 쓰기)
    print("=== PRE-VALIDATION (all anchors exact-count) ===")
    ok = True
    for name, old, _new, exp in PATCHES:
        got = c(orig, old)
        good = got == exp
        ok = ok and good
        print("  [%s] %-20s anchor count=%d expect=%d" %
              ("OK " if good else "!! ", name, got, exp))
    # 보존 확인 — 치환 후에도 살아있어야 할 핵심 변수/구조
    preserve_pre = {
        "{line1}": 1, "{nav_links}": 1, "{card1}": 1, "{code}": None,
        'id="f29-header"': 1, 'id="f29-footer"': 1,
        "return f'''": 1,
    }
    for sub, exp in preserve_pre.items():
        got = c(orig, sub)
        good = (got >= 1) if exp is None else (got == exp)
        ok = ok and good
        tag = ">=1" if exp is None else ("=%d" % exp)
        print("  [%s] preserve(%-18s)=%d expect%s" %
              ("OK " if good else "!! ", sub, got, tag))
    if not ok:
        die("pre-validation failed -- no write.")

    # 2) 변환 (in-memory, 각 1회)
    # 주의: 일부 치환은 OLD 가 NEW 의 부분문자열(예: P4 는 .disc 규칙을 유지한 채 앞에 신규 CSS 추가).
    # 이 경우 replace 후에도 OLD 카운트가 줄지 않으므로, 카운트 델타가 아니라
    # "치환 후 문자열이 실제로 바뀌었는지 + repl 이 정확히 1회 삽입됐는지"로 검증한다.
    new = orig
    for name, old, repl, _exp in PATCHES:
        prev = new
        new = new.replace(old, repl, 1)
        if new == prev:
            die("replace no-op at %s (anchor present but replace produced no change)" % name)
        # repl 이 비어있지 않으면(삭제가 아니면) 최소 1회는 존재해야 함
        if repl and repl not in new:
            die("replace verify failed at %s (repl not found after substitution)" % name)

    # 3) 사후검증
    print("=== POST-VALIDATION ===")
    ok = True
    post = {
        "20260708c": 0,          # 구버전 소멸
        "20260709b": 1,          # 신버전 1
        "judg-disc": 2,          # CSS 규칙1 + span class1
        "특정 종목의 매수·매도 추천이 아닙니다.": 1,  # judg span 으로 1회만 (disc 제거)
        'class="disc"': 0,       # disc 단락 제거
        '<nav class="navlinks">{nav_links}</nav>': 0,  # nav 제거
        "{nav_links}": 0,        # 유일 참조가 nav 였으므로 0
    }
    for sub, exp in post.items():
        got = c(new, sub)
        good = got == exp
        ok = ok and good
        lbl = sub if len(sub) <= 40 else sub[:37] + "..."
        print("  [%s] count(%-42s)=%d expect=%d" %
              ("OK " if good else "!! ", lbl, got, exp))
    # 보존 재확인
    for sub in ["{line1}", "{card1}", 'id="f29-header"', 'id="f29-footer"', "return f'''"]:
        got = c(new, sub)
        good = got >= 1
        ok = ok and good
        print("  [%s] preserve(%-18s)=%d min=1" % ("OK " if good else "!! ", sub, got))
    if not ok:
        die("post-validation failed -- no write.")

    # 4) py_compile (치환본)
    py_check(new, "patched (in-memory)")

    # 5) 바이트 증거
    ob, nb = len(orig.encode()), len(new.encode())
    print("=== BYTES: %d -> %d (delta %+d) ===" % (ob, nb, nb - ob))

    if mode == "--dry-run":
        print("=== DRY-RUN: no write. Review, then re-run --apply. ===")
        sys.exit(0)

    # 6) apply: 백업 -> 쓰기 -> 실파일 py_compile + grep
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    bak = path + ".bak_" + ts
    with open(bak, "w", encoding="utf-8") as f:
        f.write(orig)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print("=== WROTE %s (backup: %s) ===" % (path, bak))
    with open(path, "r", encoding="utf-8") as f:
        disk = f.read()
    py_check(disk, "on-disk file")
    print("=== ON-DISK GREP EVIDENCE ===")
    for a in ["20260708c", "20260709b", "judg-disc",
              'class="disc"', 'class="navlinks">{nav_links}', "{nav_links}",
              "{line1}", "id=\"f29-header\"", "id=\"f29-footer\""]:
        print("  %-30s = %d" % (a, disk.count(a)))
    print("  final bytes = %d" % len(disk.encode()))
    print()
    print("=== NEXT (수동) ===")
    print("  1) 재생성:  /usr/bin/python3 /root/krx-moneyflow/build_stock_pages.py")
    print("  2) 검증:    grep -c '20260709b' /var/www/f29-stock/005930/index.html   # =1")
    print("             grep -c 'navlinks'  /var/www/f29-stock/005930/index.html   # =0")
    print("             grep -c 'judg-disc' /var/www/f29-stock/005930/index.html   # =2")
    print("             grep -c 'class=\"disc\"' /var/www/f29-stock/005930/index.html # =0")
    print("  3) 하드리로드(Ctrl+Shift+R) 육안: footer(copyright/keep-all) 정상 렌더 확인")


if __name__ == "__main__":
    main()
