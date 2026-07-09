#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch1_1_search.py
F29 포탈 검색창 v1.0 -> v1.1 치환 패치 (추가 아님, 전체 IIFE 블록 교체)

대상: /var/www/f29-portal/index.html
전제: 라이브 실측 확정 (2026-07-09)
  - 검색 IIFE는 파일 내 정확히 1회 존재 (grep -c 'var EP="https://f29.io/stock/stocks-index.json"' == 1)
  - v1.0에는 버전 마커 없음 (이번 패치가 최초로 마커를 도입)

v1.1 수정 3건 (감리 확정):
  1) Enter 키 async-safe: ensureLoaded().then(render -> go/showEmpty)
  2) filter() exact-rank: code exact > name exact > code prefix > name includes
  3) fetch 실패 시 loadPromise=null 재시도 허용 (+ 성공 시 return allItems)

버전마커 정책 (감리 지시):
  v1.1 마커 있음      -> SKIP (이미 적용됨, 멱등)
  v1.0/무마커 IIFE 있음 -> v1.1로 교체
  알 수 없는 버전 마커  -> FAIL (수동 확인 필요, 자동 처리 금지)
  IIFE 0개 또는 2개 이상 -> FAIL (앵커 불확실, 자동 처리 금지)

patch2 / chrome.js 관련 작업은 이 스크립트 범위 밖. 절대 동시 배포 금지.
"""

import sys
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

DEFAULT_TARGET = Path("/var/www/f29-portal/index.html")
TARGET = DEFAULT_TARGET

MARKER_V11_START = "<!-- PATCH:f29-portal-search:v1.1 START -->"
MARKER_V11_END = "<!-- PATCH:f29-portal-search:v1.1 END -->"
ANY_MARKER_RE = re.compile(r"<!--\s*PATCH:f29-portal-search:v([0-9.]+)\s+START\s*-->")

EP_ANCHOR = 'var EP="https://f29.io/stock/stocks-index.json";'

# ---- v1.0 원본 블록 (라이브 실측 479~544행, 문자 그대로) ----
OLD_BLOCK = '''<script>
(function(){
  var EP="https://f29.io/stock/stocks-index.json";
  var input=document.getElementById("stockSearch");
  var box=document.getElementById("stockSearchResults");
  var empty=document.getElementById("searchEmpty");
  var btn=document.getElementById("searchBtn");
  if(!input||!box) return;
  var allItems=null,matches=[],active=-1,loadPromise=null;
  function norm(s){return (s||"").toString().toLowerCase().replace(/\\s+/g,"");}
  function ensureLoaded(){
    if(loadPromise) return loadPromise;
    loadPromise=fetch(EP).then(function(r){return r.json();})
      .then(function(j){allItems=Array.isArray(j)?j:(j.items||[]);})
      .catch(function(){allItems=[];});
    return loadPromise;
  }
  function filter(q){
    var qn=norm(q),out=[];
    if(!qn||!allItems) return out;
    for(var i=0;i<allItems.length&&out.length<8;i++){
      var it=allItems[i],code=(it.code||"").toString();
      if(norm(it.name).indexOf(qn)>-1||code.toLowerCase().indexOf(qn)===0) out.push(it);
    }
    return out;
  }
  function go(it){
    if(!it) return;
    try{if(window.gtag) gtag("event","stock_search_go",{code:it.code});}catch(e){}
    window.location.href="/stock/"+it.code+"/";
  }
  function highlight(){
    var n=box.querySelectorAll(".ssitem");
    for(var i=0;i<n.length;i++) n[i].setAttribute("data-active",i===active?"1":"");
  }
  function showEmpty(){box.style.display="none";if(empty)empty.style.display="";}
  function render(){
    matches=filter(input.value);active=-1;box.innerHTML="";
    if(!norm(input.value)){box.style.display="none";if(empty)empty.style.display="none";return;}
    if(matches.length===0){showEmpty();return;}
    if(empty)empty.style.display="none";box.style.display="";
    matches.forEach(function(it){
      var el=document.createElement("div");el.className="ssitem";
      var nm=document.createElement("span");nm.textContent=it.name;
      var cc=document.createElement("span");cc.className="ssc";cc.textContent=it.code;
      el.appendChild(nm);el.appendChild(cc);
      el.addEventListener("mousedown",function(e){e.preventDefault();go(it);});
      box.appendChild(el);
    });
  }
  input.addEventListener("focus",function(){ensureLoaded().then(render);});
  input.addEventListener("input",function(){ensureLoaded().then(render);});
  input.addEventListener("keydown",function(e){
    if(e.key==="ArrowDown"){e.preventDefault();if(matches.length){active=(active+1)%matches.length;highlight();}}
    else if(e.key==="ArrowUp"){e.preventDefault();if(matches.length){active=(active-1+matches.length)%matches.length;highlight();}}
    else if(e.key==="Enter"){e.preventDefault();go(matches[active>=0?active:0]);}
    else if(e.key==="Escape"){input.value="";render();box.style.display="none";}
  });
  input.addEventListener("blur",function(){setTimeout(function(){box.style.display="none";},200);});
  if(btn){btn.addEventListener("click",function(){
    ensureLoaded().then(function(){render();
      if(matches.length){go(matches[active>=0?active:0]);}
      else{showEmpty();input.focus();}});
  });}
})();
</script>'''

# ---- v1.1 신규 블록 (마커 포함, 수정 3건 반영) ----
NEW_BLOCK = MARKER_V11_START + "\n" + '''<script>
(function(){
  var EP="https://f29.io/stock/stocks-index.json";
  var input=document.getElementById("stockSearch");
  var box=document.getElementById("stockSearchResults");
  var empty=document.getElementById("searchEmpty");
  var btn=document.getElementById("searchBtn");
  if(!input||!box) return;
  var allItems=null,matches=[],active=-1,loadPromise=null;
  function norm(s){return (s||"").toString().toLowerCase().replace(/\\s+/g,"");}
  function ensureLoaded(){
    if(loadPromise) return loadPromise;
    loadPromise=fetch(EP).then(function(r){return r.json();})
      .then(function(j){allItems=Array.isArray(j)?j:(j.items||[]);return allItems;})
      .catch(function(){allItems=[];loadPromise=null;return allItems;});
    return loadPromise;
  }
  function filter(q){
    var qn=norm(q);
    if(!qn||!allItems) return [];
    var out=[];
    for(var i=0;i<allItems.length;i++){
      var it=allItems[i];
      var code=(it.code||"").toString();
      var codeL=code.toLowerCase();
      var nameN=norm(it.name);
      var tier=-1;
      if(codeL===qn) tier=0;
      else if(nameN===qn) tier=1;
      else if(codeL.indexOf(qn)===0) tier=2;
      else if(nameN.indexOf(qn)>-1) tier=3;
      if(tier>=0) out.push({item:it,tier:tier,idx:i});
    }
    out.sort(function(a,b){
      if(a.tier!==b.tier) return a.tier-b.tier;
      return a.idx-b.idx;
    });
    var res=[];
    for(var k=0;k<out.length&&res.length<8;k++) res.push(out[k].item);
    return res;
  }
  function go(it){
    if(!it) return;
    try{if(window.gtag) gtag("event","stock_search_go",{code:it.code});}catch(e){}
    window.location.href="/stock/"+it.code+"/";
  }
  function highlight(){
    var n=box.querySelectorAll(".ssitem");
    for(var i=0;i<n.length;i++) n[i].setAttribute("data-active",i===active?"1":"");
  }
  function showEmpty(){box.style.display="none";if(empty)empty.style.display="";}
  function render(){
    matches=filter(input.value);active=-1;box.innerHTML="";
    if(!norm(input.value)){box.style.display="none";if(empty)empty.style.display="none";return;}
    if(matches.length===0){showEmpty();return;}
    if(empty)empty.style.display="none";box.style.display="";
    matches.forEach(function(it){
      var el=document.createElement("div");el.className="ssitem";
      var nm=document.createElement("span");nm.textContent=it.name;
      var cc=document.createElement("span");cc.className="ssc";cc.textContent=it.code;
      el.appendChild(nm);el.appendChild(cc);
      el.addEventListener("mousedown",function(e){e.preventDefault();go(it);});
      box.appendChild(el);
    });
  }
  input.addEventListener("focus",function(){ensureLoaded().then(render);});
  input.addEventListener("input",function(){ensureLoaded().then(render);});
  input.addEventListener("keydown",function(e){
    if(e.key==="ArrowDown"){e.preventDefault();if(matches.length){active=(active+1)%matches.length;highlight();}}
    else if(e.key==="ArrowUp"){e.preventDefault();if(matches.length){active=(active-1+matches.length)%matches.length;highlight();}}
    else if(e.key==="Enter"){
      e.preventDefault();
      ensureLoaded().then(function(){
        render();
        if(matches.length){go(matches[active>=0?active:0]);}
        else{showEmpty();input.focus();}
      });
    }
    else if(e.key==="Escape"){input.value="";render();box.style.display="none";}
  });
  input.addEventListener("blur",function(){setTimeout(function(){box.style.display="none";},200);});
  if(btn){btn.addEventListener("click",function(){
    ensureLoaded().then(function(){render();
      if(matches.length){go(matches[active>=0?active:0]);}
      else{showEmpty();input.focus();}});
  });}
})();
</script>''' + "\n" + MARKER_V11_END


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def extract_last_script_and_check(html_text, label):
    """치환된 v1.1 스크립트만 뽑아 node --check. node 없으면 경고만 하고 계속."""
    scripts = re.findall(r"<script>(.*?)</script>", html_text, re.S)
    if not scripts:
        fail("검증용 <script> 블록을 찾지 못함 (%s)" % label)
    # v1.1 스크립트는 EP 앵커를 포함하는 마지막 script 블록
    target_js = None
    for s in reversed(scripts):
        if EP_ANCHOR in s:
            target_js = s
            break
    if target_js is None:
        fail("EP 앵커를 포함한 검색 스크립트를 찾지 못함 (%s)" % label)
    tmp_path = Path("/tmp/patch1_1_check.js")
    tmp_path.write_text(target_js, encoding="utf-8")
    try:
        r = subprocess.run(["node", "--check", str(tmp_path)],
                            capture_output=True, text=True)
    except FileNotFoundError:
        print("경고: node 미발견, 문법 체크 건너뜀 (%s)" % label)
        return
    if r.returncode != 0:
        fail("node --check 실패 (%s):\n%s" % (label, r.stderr))
    print("node --check 통과 (%s)" % label)


def main():
    dry = "--dry" in sys.argv
    target = DEFAULT_TARGET
    for a in sys.argv[1:]:
        if a.startswith("--target="):
            target = Path(a.split("=", 1)[1])
    global TARGET
    TARGET = target

    if not TARGET.exists():
        fail("대상 파일 없음: %s" % TARGET)

    text = TARGET.read_text(encoding="utf-8")
    before_bytes = len(text.encode("utf-8"))

    # 1) 이미 v1.1 적용됐는지 (멱등 SKIP)
    if MARKER_V11_START in text and MARKER_V11_END in text:
        print("SKIP: v1.1 마커 이미 존재. 변경 없음.")
        print("현재 바이트: %d" % before_bytes)
        return

    # 2) 알 수 없는 버전 마커 존재 -> FAIL
    m = ANY_MARKER_RE.search(text)
    if m and m.group(1) != "1.1":
        fail("알 수 없는 버전 마커 발견: v%s (수동 확인 필요, 자동 처리 중단)" % m.group(1))

    # 3) EP 앵커 개수로 IIFE 단일성 재확인
    ep_count = text.count(EP_ANCHOR)
    if ep_count == 0:
        fail("검색 IIFE(EP 앵커)를 찾지 못함. 대상 파일이 예상과 다름.")
    if ep_count > 1:
        fail("EP 앵커가 %d회 발견됨 (1이어야 함). 중복 IIFE 의심, 수동 확인 필요." % ep_count)

    # 4) 원본 v1.0 블록이 정확히 1회, 문자 그대로 존재하는지 확인
    old_count = text.count(OLD_BLOCK)
    if old_count == 0:
        fail(
            "OLD_BLOCK 리터럴 매칭 실패 (0회). "
            "라이브 파일이 실측 스냅샷과 문자 단위로 다릅니다. "
            "grep -n 'var EP=' 재실측 후 old_block.txt 갱신 필요. 자동 치환 중단."
        )
    if old_count > 1:
        fail("OLD_BLOCK이 %d회 발견됨 (1이어야 함). 수동 확인 필요." % old_count)

    new_text = text.replace(OLD_BLOCK, NEW_BLOCK, 1)
    after_bytes = len(new_text.encode("utf-8"))

    print("=== patch1_1_search.py ===")
    print("대상: %s" % TARGET)
    print("모드: %s" % ("DRY-RUN" if dry else "APPLY"))
    print("치환 전 바이트: %d" % before_bytes)
    print("치환 후 바이트(예상): %d (차이 %+d)" % (after_bytes, after_bytes - before_bytes))
    print("OLD_BLOCK 매칭: %d회 (정상)" % old_count)

    if dry:
        print("DRY-RUN: 실제 파일 변경 없음.")
        extract_last_script_and_check(new_text, "dry-run 시뮬레이션")
        return

    # 백업
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_path = TARGET.with_suffix(TARGET.suffix + ".search11bak.%s" % ts)
    shutil.copy2(TARGET, backup_path)
    print("백업 생성: %s" % backup_path)

    TARGET.write_text(new_text, encoding="utf-8")

    # 배포 후 3중 체크
    final_text = TARGET.read_text(encoding="utf-8")
    final_bytes = len(final_text.encode("utf-8"))
    print("배포 후 실제 바이트: %d" % final_bytes)
    if final_bytes != after_bytes:
        fail("배포 후 바이트가 예상과 다름 (예상 %d, 실제 %d). 롤백 검토 필요." % (after_bytes, final_bytes))

    if MARKER_V11_START not in final_text or MARKER_V11_END not in final_text:
        fail("배포 후 v1.1 마커 확인 실패. 롤백 검토 필요.")
    print("v1.1 마커 확인 OK")

    extract_last_script_and_check(final_text, "배포 후 실파일")

    print("=== 적용 완료 ===")
    print("롤백 명령: cp %s %s" % (backup_path, TARGET))


if __name__ == "__main__":
    main()
