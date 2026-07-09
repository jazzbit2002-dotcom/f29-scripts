#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CONTRACT-UPDATE: precheck migration record
# Applies 4 anchor-based edits to /root/CHROME_CONTRACT.md:
#   Edit1a: SS6 heading count 8->15
#   Edit1b: SS6 table -- append 7 precheck rows after the match.html row
#   Edit2 : SS7 backlog block (precheck entry) -> "none, see SS9"
#   Edit3 : SS9 history -- append PRECHECK-CHROME-MIGRATION entry after CONTRACT-UNIFY
#
# All anchor literals below were extracted PROGRAMMATICALLY (Python str.index /
# slicing on the verified original and updated contract text, converted to
# \\uXXXX escapes by code) -- never hand-typed -- and confirmed byte-exact
# before this script was assembled. No whole-file rewrite (contract SS8):
# anchor str.replace only.
#
# Usage:
#   python3 update_contract.py --dry-run
#   python3 update_contract.py --apply

import sys, datetime

TARGET = "/root/CHROME_CONTRACT.md"
EXPECTED_BEFORE_BYTES = 9354
EXPECTED_AFTER_BYTES = 10946

# ---- anchors (machine-generated, see header) ----
E1A_OLD = '\uc9c1\uc811 \ucc38\uc870 HTML 8\uac1c (\ud589\ubc88\ud638\ub294 \ucc38\uace0\uc6a9 \u2014 \uc575\ucee4\ub294 \uad6c\uc870 \uae30\ubc18\uc73c\ub85c\ub9cc, \ud589\ubc88\ud638 \uc0ac\uc6a9 \uae08\uc9c0):'
E1A_NEW = '\uc9c1\uc811 \ucc38\uc870 HTML 15\uac1c (\ud589\ubc88\ud638\ub294 \ucc38\uace0\uc6a9 \u2014 \uc575\ucee4\ub294 \uad6c\uc870 \uae30\ubc18\uc73c\ub85c\ub9cc, \ud589\ubc88\ud638 \uc0ac\uc6a9 \uae08\uc9c0):'
E1B_OLD = '| /var/www/f29-pattern-lab/match.html | lab |\n\n'
E1B_NEW = '| /var/www/f29-pattern-lab/match.html | lab |\n| /var/www/f29/precheck/index.html | pb |\n| /var/www/f29/precheck/checklist/index.html | pb |\n| /var/www/f29/precheck/full/index.html | pb |\n| /var/www/f29/precheck/position/index.html | pb |\n| /var/www/f29/precheck/principles/index.html | pb |\n| /var/www/f29/precheck/thesis/index.html | pb |\n| /var/www/f29/precheck/valuation/index.html | pb |\n\n'
E2_OLD = '## 7. \ubbf8\uc801\uc6a9 \ubc31\ub85c\uadf8\n\n- **/var/www/f29/precheck/*** \u2014 chrome=0, header=0, footer=0 (\uc2e4\uce21 \ud655\uc778)\n  - \ubcc4\ub3c4 \uc791\uc5c5\uba85: PRECHECK-CHROME-MIGRATION-AUDIT (\ub2e8\uc21c bump \uc544\ub2cc \uad6c\uc870 \uac10\uc0ac)\n  - **\uc8fc\uc758**: `index.html.chromebak.20260708_043832` \ubc31\uc5c5 \uc2e4\uc874 \u2014 7/8\uc5d0 chrome\n    \uc774\uc804\uc774 \uc2dc\ub3c4\ub410\ub2e4\uac00 \ub864\ubc31/\ubbf8\uc644\ub8cc\ub41c \uc774\ub825. \uac10\uc0ac \ucc29\uc218 \uc2dc \uc774 \ubc31\uc5c5 \ud310\ub3c5\ubd80\ud130 \uc2dc\uc791\ud560 \uac83.\n\n'
E2_NEW = '## 7. \ubbf8\uc801\uc6a9 \ubc31\ub85c\uadf8\n\n\ud604\uc7ac \uc5c6\uc74c. (precheck\ub294 PRECHECK-CHROME-MIGRATION \uc644\ub8cc\ub85c \u00a76 \ud3b8\uc785. \uc774\ub825\uc740 \u00a79 \ucc38\uc870)\n\n'
E3_OLD = 'U1~U8 \uc7ac\uc2e4\uce21 \ud6c4 \uc774 \ud1b5\ud569\ubcf8\uc73c\ub85c \ub2e8\uc77c\ud654. /root/CHROME_CONTRACT.md \uc720\uc77c \uc815\ubcf8 \ud655\uc815.\n'
E3_NEW = 'U1~U8 \uc7ac\uc2e4\uce21 \ud6c4 \uc774 \ud1b5\ud569\ubcf8\uc73c\ub85c \ub2e8\uc77c\ud654. /root/CHROME_CONTRACT.md \uc720\uc77c \uc815\ubcf8 \ud655\uc815.\n- **v20260709b \ud6c4\uc18d \u2014 PRECHECK-CHROME-MIGRATION** (2026-07-09):\n  /var/www/f29/precheck/*** 7\uac1c(index/checklist/full/position/principles/\n  thesis/valuation)\ub97c \uacf5\uc6a9 chrome \uacc4\uc57d\uc73c\ub85c \ud3b8\uc785.\n  \uac10\uc0ac: `index.html.chromebak.20260708_043832`\ub294 \uc801\uc6a9 \ud6c4 \ub864\ubc31\uc774 \uc544\ub2c8\ub77c \ucc29\uc218 \uc804\n  \uc6d0\ubcf8 \uc2a4\ub0c5\uc0f7\uc73c\ub85c \ud310\uc815(7\uac1c \uc804\uccb4 chrome \ucc38\uc870 0\uac74 \ud655\uc778, \uc0ac\uace0 \uc774\ub825 \uc544\ub2d8).\n  NAV\ub294 A\uc548(NAV6 \uc218\uc6a9, \ud398\uc774\uc9c0\ubcc4 \uc608\uc678 \ubbf8\uc2e0\uc124)\uc73c\ub85c \ud655\uc815.\n  \uc790\uccb4 header(portal-nav: \ub85c\uace0+3\ub9c1\ud06c+\uc5b8\uc5b4\ubc84\ud2bc)\u00b7footer(disclaimer/copyright/\n  contact) \uc804\uccb4 \uc81c\uac70 \u2192 f29-header/f29-footer\ub85c \ub300\uccb4, f29:lang \uc218\uc2e0\uc790 \ucd94\uac00\n  (\uc5ed\ud638\ucd9c \uc5c6\uc74c). \ubcf8\ubb38 \ucef4\ud50c\ub77c\uc774\uc5b8\uc2a4 \ubb38\uad6c(`.disclaimer` \ubb38\ub2e8)\u00b7\ud558\uc704 6\uac1c \ub0b4\ubd80\n  step nav(`<nav class="nav">`)\ub294 \ubcf4\uc874.\n  \ud328\uce58 \uc2a4\ud06c\ub9bd\ud2b8 v2.1\u2192v2.3: \uc11c\ubc84 dry-run\uc5d0\uc11c 2\ud68c \uc5f0\uc18d \uc548\uc804\ud558\uac8c abort\ub41c \ub4a4 \ubcf4\uc815\n  \u2014 \u2460 \ud558\uc704 6\uac1c \ubcf8\ubb38\uc5d0 \ud3ec\ud138 nav \uc678 \ub0b4\ubd80 step nav\uac00 \uc788\uc5b4 \uc804\uc5ed `</nav>` \uce74\uc6b4\ud2b8\uac00\n  2\uc600\ub358 \ubb38\uc81c(\ud3ec\ud138 nav \uc2dc\uc791 \uc774\ud6c4 \ucd5c\uadfc\uc811 `</nav>`\uae4c\uc9c0\ub9cc \uc81c\uac70\ud558\ub3c4\ub85d \uc218\uc815)\n  \u2461 CSS \uaddc\uce59\uc774 \uc544\ub2cc CJK \ubb38\uc11c\ud654 \uc8fc\uc11d(`.portal-nav` \uc5b8\uae09)\uc774 \uc794\uc874\ud574 after-check\n  \uc2e4\ud328(\uad6c\uc870\uc801 ASCII \ub9c8\ucee4 \ub9e4\uce6d\uc73c\ub85c \uc81c\uac70 \ub85c\uc9c1 \ucd94\uac00).\n  7\ud30c\uc77c dry-run \uc804\ubd80 PASS \ud6c4 \uc6d0\uc790\uc801 \uc77c\uad04 apply, \ubc31\uc5c5\n  `*.bak_chromemig_20260709_111738` 7\uac1c \uc0dd\uc131. \ub3c5\ub9bd \uc7ac\uc2e4\uce21(grep)\uc73c\ub85c\n  portal-nav/footer/Copyright \uc804\ubd80 0, \ubcf8\ubb38 \ubcf4\uc874 \uc804\ubd80 \uc77c\uce58 \ud655\uc778.\n  \u00a76\uc5d0 7\uac1c \ucd94\uac00(data-active="pb"), \u00a77 \ubc31\ub85c\uadf8 \uc0ad\uc81c.\n'

EDITS = [("Edit1a-heading", E1A_OLD, E1A_NEW),
         ("Edit1b-table-rows", E1B_OLD, E1B_NEW),
         ("Edit2-backlog-clear", E2_OLD, E2_NEW),
         ("Edit3-history-append", E3_OLD, E3_NEW)]


class Abort(Exception):
    pass


def run(mode):
    with open(TARGET, encoding="utf-8") as f:
        text = f.read()

    before_bytes = len(text.encode("utf-8"))
    print(f"[BEFORE] {TARGET}: {before_bytes} bytes (expected {EXPECTED_BEFORE_BYTES})")
    if before_bytes != EXPECTED_BEFORE_BYTES:
        raise Abort(f"before-byte mismatch: got {before_bytes}, expected {EXPECTED_BEFORE_BYTES}. "
                    f"Contract may have changed since this script was written -- re-verify anchors before editing.")

    for name, old, new in EDITS:
        c_old = text.count(old)
        print(f"[CHECK] {name}: old_anchor_count={c_old} (expect 1)")
        if c_old != 1:
            raise Abort(f"{name}: anchor found {c_old} times, expected exactly 1. Abort, no write.")

    t = text
    for name, old, new in EDITS:
        if t.count(old) != 1:
            raise Abort(f"{name}: anchor count changed mid-sequence (unexpected overlap). Abort.")
        t = t.replace(old, new, 1)
        print(f"[APPLIED-IN-MEMORY] {name}")

    after_bytes = len(t.encode("utf-8"))
    print(f"[AFTER] computed: {after_bytes} bytes (expected {EXPECTED_AFTER_BYTES})")
    if after_bytes != EXPECTED_AFTER_BYTES:
        raise Abort(f"after-byte mismatch: got {after_bytes}, expected {EXPECTED_AFTER_BYTES}. Abort, no write.")

    if text.count(E1A_NEW) > 0:
        raise Abort("idempotency: post-edit heading (E1A_NEW) already present before edit -- "
                    "contract appears already updated. Abort, no write.")

    print("\n=== DRY-RUN PASS: all anchors unique, byte math checks out, no prior application detected ===")

    if mode == "--apply":
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = f"{TARGET}.bak_precheck_{ts}"
        with open(backup, "w", encoding="utf-8") as f:
            f.write(text)
        with open(TARGET, "w", encoding="utf-8") as f:
            f.write(t)
        print(f"[WROTE] {TARGET}  (backup {backup})")
        print("=== APPLY COMPLETE. Run grep verification next. ===")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode not in ("--dry-run", "--apply"):
        print("usage: update_contract.py [--dry-run|--apply]")
        sys.exit(2)
    try:
        run(mode)
    except Abort as e:
        print(f"[ABORT] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
