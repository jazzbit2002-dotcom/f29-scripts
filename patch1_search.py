#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# patch1_search.py — F29 포탈 종목 검색창(패치1) 추가 전용 패치
#
# 원칙:
#   - additive only: 기존 라인은 한 글자도 변경하지 않음. ASCII 앵커 5곳에 신규 블록만 삽입.
#   - 멱등(idempotent): 이미 적용됐으면 아무것도 하지 않고 종료(코드 0).
#   - 셀프 검증: 앵커 각 1회 등장 확인 → 삽입 → 최종 파일에 신규 id 존재 확인.
#   - 백업: 실행 시 .searchbak.<timestamp> 자동 생성.
#
# 사용:
#   python3 patch1_search.py            # 실제 적용
#   python3 patch1_search.py --dry      # 미적용, 삽입 위치만 리포트
#
# 배포 흐름(모바일): 이 파일을 GitHub 웹에 업로드 → 서버에서 curl 로 받아 실행.
#   SSH 한글 붙여넣기 없음(한글은 이 파일 안에 있음), heredoc 없음.

import sys, os, io, time, re

PATH = "/var/www/f29-portal/index.html"
DRY  = "--dry" in sys.argv

# ── 삽입 블록 ────────────────────────────────────────────────────────────

MARKUP = (
'    <div id="stockSearchWrap">\n'
'      <input id="stockSearch" type="text" placeholder="" autocomplete="off" inputmode="search" />\n'
'      <button id="searchBtn" type="button"></button>\n'
'      <div id="stockSearchResults" style="display:none"></div>\n'
'      <span id="searchEmpty" style="display:none"></span>\n'
'    </div>\n'
)

CSS = (
'  /* -- 종목 검색창 (패치1) -- */\n'
'  #stockSearchWrap{position:relative;display:flex;flex-wrap:wrap;gap:8px;max-width:440px;margin:26px auto 0}\n'
'  #stockSearch{flex:1 1 220px;box-sizing:border-box;padding:11px 14px;font-size:.95rem;background:var(--card2);border:1px solid var(--line2);border-radius:10px;color:var(--txt);font-family:inherit;outline:none;transition:border-color .16s}\n'
'  #stockSearch:focus{border-color:var(--teal)}\n'
'  #stockSearch::placeholder{color:var(--txt3)}\n'
'  #searchBtn{flex:0 0 auto;padding:11px 20px;font-size:.9rem;font-weight:700;background:var(--teal);color:#0A0E17;border:none;border-radius:10px;cursor:pointer;font-family:inherit;transition:opacity .16s}\n'
'  #searchBtn:hover{opacity:.88}\n'
'  #stockSearchResults{position:absolute;top:calc(100% + 6px);left:0;right:0;z-index:40;background:var(--card);border:1px solid var(--line2);border-radius:10px;max-height:320px;overflow-y:auto;box-shadow:0 12px 32px rgba(0,0,0,.4)}\n'
'  #stockSearchResults .ssitem{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:11px 14px;font-size:.9rem;color:var(--txt);cursor:pointer;border-bottom:1px solid var(--line)}\n'
'  #stockSearchResults .ssitem:last-child{border-bottom:none}\n'
'  #stockSearchResults .ssitem[data-active="1"],#stockSearchResults .ssitem:hover{background:var(--card2);color:var(--teal)}\n'
'  #stockSearchResults .ssitem .ssc{color:var(--txt3);font-size:.82rem;font-family:ui-monospace,monospace}\n'
'  #searchEmpty{display:block;margin-top:8px;font-size:.8rem;color:var(--txt3);text-align:center}\n'
)

TSEARCH = (
'var TSEARCH = {\n'
'  ko:{searchPh:"투자 중인 종목을 입력하세요",searchBtn:"검색",searchEmpty:"해당 종목 페이지가 아직 없습니다"},\n'
'  en:{searchPh:"Enter a stock you\'re watching",searchBtn:"Search",searchEmpty:"No page for this stock yet"},\n'
'  zh:{searchPh:"输入您关注的股票代码或名称",searchBtn:"搜索",searchEmpty:"该股票的页面尚未生成。"},\n'
'  ja:{searchPh:"気になる銘柄を入力してください",searchBtn:"検索",searchEmpty:"この銘柄のページはまだありません"}\n'
'};\n'
)

WIRING = (
'  var _ts=(typeof TSEARCH!=="undefined"&&(TSEARCH[l]||TSEARCH.ko))||null;\n'
'  if(_ts){ set("searchBtn",_ts.searchBtn); set("searchEmpty",_ts.searchEmpty);\n'
'    var _sp=document.getElementById("stockSearch"); if(_sp) _sp.placeholder=_ts.searchPh; }\n'
)

SCRIPT = r'''<script>
(function(){
  var EP="https://f29.io/stock/stocks-index.json";
  var input=document.getElementById("stockSearch");
  var box=document.getElementById("stockSearchResults");
  var empty=document.getElementById("searchEmpty");
  var btn=document.getElementById("searchBtn");
  if(!input||!box) return;
  var allItems=null,matches=[],active=-1,loadPromise=null;
  function norm(s){return (s||"").toString().toLowerCase().replace(/\s+/g,"");}
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
</script>
'''

# ── 앵커 정의: (이름, 앵커문자열, 삽입위치 'after'|'before', 삽입블록) ─────────
ANCHORS = [
    ("markup",  '    <p class="sub" id="heroSub"></p>\n', "after",  MARKUP),
    ("css",     '</style>',                                "before", CSS),
    ("tsearch", 'var T = {',                               "before", TSEARCH),
    ("wiring",  '  set("disclaimer",t.disclaimer);\n',     "after",  WIRING),
    ("script",  '</body>',                                 "before", SCRIPT),
]

def fail(msg):
    print("[FAIL] " + msg); sys.exit(1)

def main():
    if not os.path.exists(PATH):
        fail("파일 없음: " + PATH)
    with io.open(PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 멱등 체크
    if 'id="stockSearch"' in content:
        print("[SKIP] 이미 적용됨 (id=\"stockSearch\" 존재). 무동작 종료."); sys.exit(0)

    before_bytes = len(content.encode("utf-8"))

    # 앵커 각 1회 등장 검증
    for name, anchor, _, _ in ANCHORS:
        c = content.count(anchor)
        if c != 1:
            fail("앵커 '%s' 등장 %d회 (정확히 1회여야 함): %r" % (name, c, anchor[:40]))
    print("[OK] 앵커 5개 각 1회 등장 확인")

    if DRY:
        for name, anchor, pos, _ in ANCHORS:
            idx = content.index(anchor)
            line = content[:idx].count("\n") + 1
            print("  - %-8s 앵커 라인 ~%d (%s 삽입)" % (name, line, pos))
        print("[DRY] 미적용 종료."); sys.exit(0)

    # 삽입 실행 (뒤에서 앞 순서 무관 — 각 앵커는 고유 문자열이라 안전)
    new = content
    for name, anchor, pos, block in ANCHORS:
        idx = new.index(anchor)
        if pos == "after":
            cut = idx + len(anchor)
        else:  # before
            cut = idx
        new = new[:cut] + block + new[cut:]

    # 백업
    ts = time.strftime("%Y%m%d%H%M")
    bak = PATH + ".searchbak." + ts
    with io.open(bak, "w", encoding="utf-8") as f:
        f.write(content)

    # 쓰기
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(new)

    after_bytes = len(new.encode("utf-8"))

    # 최종 검증: 신규 id 5종 존재
    for need in ['id="stockSearch"','id="searchBtn"','id="stockSearchResults"',
                 'id="searchEmpty"','var TSEARCH =','stock_search_go']:
        if need not in new:
            fail("삽입 후 누락: " + need)

    print("[DONE] 패치1 적용 완료")
    print("  백업: " + bak)
    print("  바이트: %d -> %d (+%d)" % (before_bytes, after_bytes, after_bytes-before_bytes))
    print("  ※ 서버 wc -c 는 UTF-8 바이트 기준이라 위 after 값과 일치해야 함")

if __name__ == "__main__":
    main()
