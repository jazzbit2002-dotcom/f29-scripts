#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_chrome_contract.py
f29-chrome.js contract 보강 (B4 contact + B5 f29:lang) + index/pro 버전쿼리 갱신

대상:
  1) /var/www/f29-shared/f29-chrome.js   (현재 실측 8,845 bytes)
  2) /root/f29/public/index.html         (?v=20260708c -> 20260709a)
  3) /root/f29/public/pro.html           (?v=20260708c -> 20260709a)

방식: whole-file 금지. 실측 리터럴 OLD_BLOCK 치환 (한글 바이트 무접촉).

B4 contact:
  - CONTACT_LABEL 4언어 딕셔너리 신설
  - admin + String.fromCharCode(64) + "f29"+".io" 조립 (평문 mailto 금지, 기존 포털 방식 계승)
  - contactHTML()를 footLinksHTML() 끝에 append -> applyLang의 footLinksHTML 재렌더로 언어전환 자동 반영
    (contact 갱신용 별도 applyLang 배선 불필요 = 표면 최소화)

B5 language event:
  - applyLang(lang) 끝에 window.dispatchEvent(new CustomEvent("f29:lang",{detail:{lang}})) (try/catch)
  - 리스너 없는 페이지(risk index/pro)에선 no-op = 무해
  - 포털 수신 리스너는 patch2 소속 (이 패치는 포털 무접촉)

버전마커: chrome.js 내부 주석 CONTRACT:v20260709a 삽입

멱등:
  chrome.js  : CONTRACT:v20260709a 주석 있으면 SKIP
  index/pro  : ?v=20260709a 이미 있으면 해당 파일 SKIP / ?v=20260708c 있으면 치환 / 둘 다 없으면 FAIL

범위 밖(수정 금지): /var/www/f29-portal/index.html (nav/footer/삽입 전부 patch2 소속)
"""

import sys
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

CHROME = Path("/var/www/f29-shared/f29-chrome.js")
INDEX = Path("/root/f29/public/index.html")
PRO = Path("/root/f29/public/pro.html")

VER_OLD = "20260708c"
VER_NEW = "20260709a"
CONTRACT_MARK = "CONTRACT:v20260709a"

# ---------------- chrome.js 치환 정의 ----------------

# [치환1] DISCLAIMER 블록 뒤에 CONTACT_LABEL + contactHTML + 버전마커 삽입
C1_OLD = '''  var DISCLAIMER={
    ko:"F29는 시장 위험 상태와 돈의 흐름을 정리해 보여주는 참고 도구입니다. 매수·매도 신호가 아니며, 투자 판단과 그 결과는 본인에게 있습니다.",
    en:"F29 is a reference tool that organizes market risk states and money flow. It is not a buy/sell signal; investment decisions and their outcomes are your own.",
    zh:"F29 是整理市场风险状态与资金流向的参考工具。并非买卖信号，投资决策及其结果由您自行承担。",
    ja:"F29 は市場のリスク状態と資金の流れを整理して示す参考ツールです。売買シグナルではなく、投資判断とその結果はご自身に帰属します。"
  };'''

C1_NEW = C1_OLD + '''

  // ''' + CONTRACT_MARK + ''' (B4 contact + B5 f29:lang)
  var CONTACT_LABEL={
    ko:"문의 및 제안",
    en:"Contact & suggestions",
    zh:"咨询与建议",
    ja:"お問い合わせ・ご提案"
  };
  function contactHTML(){
    var u="admin", d="f29"+".io", at=String.fromCharCode(64);
    return '<span class="f29-foot-contact">'+CONTACT_LABEL[LANG]+' '+u+at+d+'</span>';
  }'''

# [치환2] footLinksHTML() -> 끝에 contact append
C2_OLD = '''  function footLinksHTML(){
    return NAV.map(function(n){
      return '<a href="'+n.href+'" data-nid="'+n.id+'">'+n[LANG]+'</a>';
    }).join('<span class="sep">|</span>');
  }'''

C2_NEW = '''  function footLinksHTML(){
    return NAV.map(function(n){
      return '<a href="'+n.href+'" data-nid="'+n.id+'">'+n[LANG]+'</a>';
    }).join('<span class="sep">|</span>')
    + '<span class="sep">|</span>' + contactHTML();
  }'''

# [치환3] applyLang() -> 끝에 f29:lang 발신
C3_OLD = '''  function applyLang(lang){
    if(!NAV[0][lang]) return;
    LANG=lang;
    var links=document.getElementById("f29-links");
    var flinks=document.getElementById("f29-foot-links");
    var dis=document.getElementById("f29-foot-dis");
    if(links) links.innerHTML=navLinksHTML();
    if(flinks) flinks.innerHTML=footLinksHTML();
    if(dis) dis.textContent=DISCLAIMER[lang];
    document.querySelectorAll(".f29-lang button").forEach(function(b){
      b.classList.toggle("on", b.getAttribute("data-lang")===lang);
    });
  }'''

C3_NEW = '''  function applyLang(lang){
    if(!NAV[0][lang]) return;
    LANG=lang;
    var links=document.getElementById("f29-links");
    var flinks=document.getElementById("f29-foot-links");
    var dis=document.getElementById("f29-foot-dis");
    if(links) links.innerHTML=navLinksHTML();
    if(flinks) flinks.innerHTML=footLinksHTML();
    if(dis) dis.textContent=DISCLAIMER[lang];
    document.querySelectorAll(".f29-lang button").forEach(function(b){
      b.classList.toggle("on", b.getAttribute("data-lang")===lang);
    });
    try{ window.dispatchEvent(new CustomEvent("f29:lang",{detail:{lang:lang}})); }catch(e){}
  }'''

CHROME_REPLACEMENTS = [
    ("DISCLAIMER+CONTACT", C1_OLD, C1_NEW),
    ("footLinksHTML", C2_OLD, C2_NEW),
    ("applyLang", C3_OLD, C3_NEW),
]


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def node_check(js_text, label):
    tmp = Path("/tmp/chrome_check.js")
    tmp.write_text(js_text, encoding="utf-8")
    try:
        r = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
    except FileNotFoundError:
        print("경고: node 미발견, 문법 체크 건너뜀 (%s)" % label)
        return
    if r.returncode != 0:
        fail("node --check 실패 (%s):\n%s" % (label, r.stderr))
    print("node --check 통과 (%s)" % label)


def plan_chrome():
    """chrome.js 사전검증. 반환: ('skip'|'apply', new_text or None, before, after)."""
    if not CHROME.exists():
        fail("chrome.js 없음: %s" % CHROME)
    text = CHROME.read_text(encoding="utf-8")
    before = len(text.encode("utf-8"))
    if CONTRACT_MARK in text:
        return ("skip", None, before, before)
    new_text = text
    for name, old, new in CHROME_REPLACEMENTS:
        cnt = new_text.count(old)
        if cnt != 1:
            fail("chrome.js 앵커 '%s' 매칭 %d회 (1이어야 함). 실측 스냅샷과 불일치, 자동 중단." % (name, cnt))
        new_text = new_text.replace(old, new, 1)
    after = len(new_text.encode("utf-8"))
    node_check(new_text, "chrome.js 치환본")
    return ("apply", new_text, before, after)


def plan_version(path):
    """버전쿼리 사전검증. 반환: ('skip'|'apply', new_text or None, cnt)."""
    if not path.exists():
        fail("파일 없음: %s" % path)
    text = path.read_text(encoding="utf-8")
    tok_new = "f29-chrome.js?v=" + VER_NEW
    tok_old = "f29-chrome.js?v=" + VER_OLD
    if tok_new in text:
        return ("skip", None, 0)
    cnt = text.count(tok_old)
    if cnt == 0:
        m = re.search(r"f29-chrome\.js\?v=([0-9a-z]+)", text)
        if m:
            fail("%s: 알 수 없는 chrome.js 버전 ?v=%s (기대 %s). 수동 확인." % (path.name, m.group(1), VER_OLD))
        fail("%s: f29-chrome.js?v=%s 참조를 찾지 못함." % (path.name, VER_OLD))
    return ("apply", text.replace(tok_old, tok_new), cnt)


def main():
    global CHROME, INDEX, PRO
    dry = "--dry" in sys.argv
    for a in sys.argv[1:]:
        if a.startswith("--chrome="):
            CHROME = Path(a.split("=", 1)[1])
        elif a.startswith("--index="):
            INDEX = Path(a.split("=", 1)[1])
        elif a.startswith("--pro="):
            PRO = Path(a.split("=", 1)[1])

    # ===== PHASE 1: 사전검증 (디스크 쓰기 없음) — 하나라도 FAIL이면 전부 중단 =====
    c_action, c_new, c_before, c_after = plan_chrome()
    i_action, i_new, i_cnt = plan_version(INDEX)
    p_action, p_new, p_cnt = plan_version(PRO)

    print("=== 사전검증 통과 ===")
    print("chrome.js : %s (%d -> %d, %+d)" % (c_action, c_before, c_after, c_after - c_before))
    print("index.html: %s (%d곳)" % (i_action, i_cnt))
    print("pro.html  : %s (%d곳)" % (p_action, p_cnt))

    if dry:
        print("\n=== DRY-RUN 종료 (변경 없음) ===")
        return

    # ===== PHASE 2: 쓰기 (모든 검증 통과 후에만 진입) =====
    ts = datetime.now().strftime("%Y%m%d%H%M%S")

    if c_action == "apply":
        bak = CHROME.with_suffix(CHROME.suffix + ".contractbak.%s" % ts)
        shutil.copy2(CHROME, bak)
        CHROME.write_text(c_new, encoding="utf-8")
        final = CHROME.read_text(encoding="utf-8")
        if len(final.encode("utf-8")) != c_after or CONTRACT_MARK not in final:
            fail("chrome.js 배포 후 검증 실패. 롤백: cp %s %s" % (bak, CHROME))
        node_check(final, "chrome.js 실파일")
        print("chrome.js 적용. 롤백: cp %s %s" % (bak, CHROME))
    else:
        print("chrome.js SKIP (마커 존재)")

    for path, action, new_text in [(INDEX, i_action, i_new), (PRO, p_action, p_new)]:
        if action == "apply":
            bak = path.with_suffix(path.suffix + ".verbak.%s" % ts)
            shutil.copy2(path, bak)
            path.write_text(new_text, encoding="utf-8")
            if ("f29-chrome.js?v=" + VER_NEW) not in path.read_text(encoding="utf-8"):
                fail("%s: 배포 후 새 버전 쿼리 확인 실패. 롤백: cp %s %s" % (path.name, bak, path))
            print("%s 적용 (?v=%s). 롤백: cp %s %s" % (path.name, VER_NEW, bak, path))
        else:
            print("%s SKIP (이미 ?v=%s)" % (path.name, VER_NEW))

    print("\n=== APPLY 종료 ===")


if __name__ == "__main__":
    main()
