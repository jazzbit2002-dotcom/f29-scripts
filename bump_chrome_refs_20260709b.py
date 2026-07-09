#!/usr/bin/env python3
# bump_chrome_refs_20260709b.py
# chrome.js 버전쿼리 bump: ?v=20260709a -> ?v=20260709b (참조 3파일 동시)
# 원자적: 전 파일 사전검증(각 1회 정확 매칭) 통과해야만 전체 쓰기. 부분적용 금지.
# ASCII 전용(파일명·경로만) — 그래도 배포 편의상 GitHub->curl 권장.
# 사용: python3 bump_chrome_refs_20260709b.py --dry-run
#       python3 bump_chrome_refs_20260709b.py --apply

import sys, os, datetime

OLD = "f29-chrome.js?v=20260709a"
NEW = "f29-chrome.js?v=20260709b"
FILES = [
    "/root/f29/public/index.html",
    "/root/f29/public/pro.html",
    "/var/www/f29-portal/index.html",
]


def die(msg):
    print("ABORT: " + msg)
    sys.exit(1)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "--dry-run"
    if mode not in ("--dry-run", "--apply"):
        die("usage: bump_chrome_refs_20260709b.py [--dry-run|--apply]")
    # 인자로 파일 목록 오버라이드 (테스트용)
    files = sys.argv[2:] if len(sys.argv) > 2 else FILES

    print("=== PRE-VALIDATION (all files) ===")
    ok = True
    state = {}
    for p in files:
        if not os.path.exists(p):
            ok = False; print("  [!! ] MISSING: " + p); continue
        s = open(p, "r", encoding="utf-8").read()
        na, nb = s.count(OLD), s.count(NEW)
        state[p] = s
        if nb >= 1 and na == 0:
            print("  [OK*] ALREADY b: %s (a=%d b=%d) -- skip" % (p, na, nb))
        elif na == 1 and nb == 0:
            print("  [OK ] ready    : %s (a=%d b=%d)" % (p, na, nb))
        else:
            ok = False
            print("  [!! ] ambiguous: %s (a=%d b=%d) expect a=1 b=0" % (p, na, nb))
    if not ok:
        die("pre-validation failed -- no write to any file.")

    # 전 파일 통과 -> 전체 쓰기
    if mode == "--dry-run":
        for p in files:
            s = state[p]
            if s.count(OLD) == 1:
                print("  would bump: %s" % p)
        print("=== DRY-RUN: no write. ===")
        sys.exit(0)

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    print("=== APPLY ===")
    for p in files:
        s = state[p]
        if s.count(OLD) != 1:
            print("  skip (already b): %s" % p); continue
        open(p + ".bak_" + ts, "w", encoding="utf-8").write(s)
        open(p, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
        disk = open(p, "r", encoding="utf-8").read()
        print("  bumped: %s  (a=%d b=%d)  bak=.bak_%s"
              % (p, disk.count(OLD), disk.count(NEW), ts))
    print("=== DONE ===")


if __name__ == "__main__":
    main()
