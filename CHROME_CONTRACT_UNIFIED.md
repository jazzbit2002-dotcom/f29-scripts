# CHROME_CONTRACT.md — f29-chrome.js 공용 컴포넌트 계약 (v20260709b, UNIFIED)

정본 JS:
- /var/www/f29-shared/f29-chrome.js (11,257 bytes, 내부 마커 `// CONTRACT:v20260709b`)
- 웹 경로: /shared/f29-chrome.js

**유일 정본 문서: /root/CHROME_CONTRACT.md (이 파일)**
- 운영 규칙: 새 세션 시작 시 `cat /root/CHROME_CONTRACT.md` 출력을 회수해 첨부한다.
  채팅/로컬 사본은 참고용이며, 서버 실측과 이 파일이 항상 canonical이다.
- CONTRACT-UNIFY (2026-07-09 09:12 UTC 재실측 기준): 채팅 정본과 서버 신규
  생성본의 이원화를 이 문서로 통합. 이후 계약 개정은 이 파일에서만 한다.

기준:
- 2026-07-09 라이브 실측 (U1~U8 재실측 스윕)
- B4 contact / B5 f29:lang event / B6 copyright·f29-foot-copy·keep-all
- STOCK-FACTORY-CONTRACT-SYNC + MOBILE-VISUAL-FIX 반영
- GLOBAL-CHROME-REF-BUMP-20260709b 반영

chrome.js를 수정하거나 새 페이지에 적용할 때 이 계약을 위반하면 안 된다.

---

## 1. Mount 규약

```
head:  <script src="/shared/f29-chrome.js?v=<버전>" data-active="<id|빈값>" defer></script>
body:  <div id="f29-header"></div>
       (page content)
       <div id="f29-footer"></div>
```

- 실행 시점: DOMContentLoaded (readyState가 loading이 아니면 즉시)
- `#f29-header`/`#f29-footer` 없는 페이지에선 해당 mount no-op (null-safe)
- CSS·웹폰트(Pretendard, JetBrains Mono)는 chrome.js가 1회 자동 주입
- 페이지별 자체 nav/footer/copyright/disclaimer 하드코딩은 금지.
  예외 2건만 허용: ① noscript nav ② 종목 페이지 본문형 `.judg-disc`
  (종목 특화 컴플라이언스 문구 — footer가 아닌 본문 소속, 안 B 판정)

## 2. NAV / data-active 규약

NAV 6개 (SSOT — 새 서비스는 chrome.js NAV 배열 한 줄 추가로 전 페이지 자동 반영):

| id | 경로 |
|---|---|
| kr | /kr-moneyflow |
| weight | /weight |
| us | /moneyflow |
| risk | /index.html, /pro.html |
| lab | /lab/, /lab/match |
| pb | /precheck |

- `document.currentScript`의 data-active로 하이라이트. 빈 값("")/미매칭 → 하이라이트 없음
- 빈 값 사용처: portal, stock (stock은 NAV 미승격 — B-3 확정)
- stock 승격 재검토 조건: ① /stock/ 허브 페이지 신설 ② GA4 /stock/* 착지·재방문 유의미 실측

## 3. Footer SSOT

footer 단일 출처는 chrome.js다. 구성:

- **disclaimer**: `DISCLAIMER[LANG]` (4언어) → `#f29-foot-dis`
- **contact**: `CONTACT_LABEL[LANG]` + `contactHTML()` (v20260709a 신설)
  - 이메일은 `"admin"+String.fromCharCode(64)+"f29"+".io"` 런타임 조립
  - 평문 mailto:admin@f29.io 하드코딩 금지 (스크래핑 방어)
- **copyright**: `COPYRIGHT[LANG]` (v20260709b 신설, 4언어 3줄: © 표시/보호 대상/금지·제재)
  → `#f29-foot-copy`. ko 문안은 구 포털 COPY 승계, 연도 "2026" 하드코딩(동적 연도 별건)
- 줄바꿈은 `\n` + CSS `white-space:pre-line` — textContent 패턴 유지, innerHTML/`<br>` 금지
- CSS 개행 규약: `.f29-foot-dis`·`.f29-foot-copy` 모두
  `word-break:keep-all; overflow-wrap:break-word` 필수 (CJK 어절 절단 금지)
- 페이지별 자체 footer/disclaimer/copyright는 제거 대상(숨김 아닌 제거).
  수정은 chrome.js 정본에서만.

## 4. Language 규약

- 내부 상태: `LANG` (기본 "ko", localStorage 미사용)
- **page → chrome**: `window.F29Chrome.setLang(lang)`
- **chrome → page** (v20260709a): applyLang 끝에서
  `window.dispatchEvent(new CustomEvent("f29:lang",{detail:{lang:lang}}))` (try/catch)
- 표준 수신: `window.addEventListener("f29:lang", function(e){ if(e&&e.detail&&e.detail.lang){ setLang(e.detail.lang); } });`
- **루프 방지 절대 규칙**: 페이지 setLang은 F29Chrome.setLang을 역호출하지 않는다.
  방향은 단방향 2개뿐. 리스너 없는 페이지에서 f29:lang은 no-op — 무해.
- 페이지 본문 다국어는 각 페이지 T객체 소관 (chrome.js 범위 밖)

## 5. Cache / 버전 배포 규약

- nginx: `/shared/` → `/var/www/f29-shared/` alias, Cache-Control max-age=300 (5분)
- `/stock/` → `/var/www/f29-stock/` alias, max-age=600
- 버전쿼리 컨벤션: `?v=YYYYMMDD[a-z]` — 현재 **20260709b**
- 버전쿼리 bump 직후에도 브라우저 하드리로드(Ctrl+Shift+R) 필요
- **chrome.js 본체 수정 시 §6 참조 목록 전부 동일 버전으로 동시 갱신. 부분 갱신 금지.**
- 배포는 원자적 2단계(전 검증 → 쓰기) 스크립트로만. 부분적용 금지.

## 6. 20260709b 적용 참조 목록 (2026-07-09 09:12 UTC 실측)

직접 참조 HTML 8개 (행번호는 참고용 — 앵커는 구조 기반으로만, 행번호 사용 금지):

| 파일 | data-active |
|---|---|
| /root/f29/public/index.html | risk |
| /root/f29/public/pro.html | risk |
| /var/www/f29-portal/index.html | "" |
| /root/krx-moneyflow/web/index.html | kr |
| /root/krx-moneyflow/web/weight.html | weight |
| /root/moneyflow/index.html | us |
| /var/www/f29-pattern-lab/index.html | lab |
| /var/www/f29-pattern-lab/match.html | lab |

템플릿 단위 1개 (**개별 산출물 나열 금지**):

- 생성 정본: /root/krx-moneyflow/build_stock_pages.py (data-active="")
  - 출력: /var/www/f29-stock/{code}/index.html 전체 (306개)
  - 버전 bump 이행 방식: 생성기 내 버전 문자열 1곳 수정 →
    cron(평일 05:20 UTC) 또는 수동 재실행으로 전체 재생성.
    이것이 이 템플릿의 "동시 갱신" 이행 방식(개별 파일 동시 수정 아님).

이후 chrome.js 적용 페이지가 늘면 이 목록에 추가하고 전부 갱신.

## 7. 미적용 백로그

- **/var/www/f29/precheck/*** — chrome=0, header=0, footer=0 (실측 확인)
  - 별도 작업명: PRECHECK-CHROME-MIGRATION-AUDIT (단순 bump 아닌 구조 감사)
  - **주의**: `index.html.chromebak.20260708_043832` 백업 실존 — 7/8에 chrome
    이전이 시도됐다가 롤백/미완료된 이력. 감사 착수 시 이 백업 판독부터 시작할 것.

## 8. 배포 방식 / 검증 규약

- whole-file 재작성 금지 (CJK 오염 위험). 실측 리터럴 앵커 치환 스크립트만.
- CJK 문안 포함 스크립트/문서: GitHub 업로드 → curl 반입만. SSH 붙여넣기 절대 금지.
- 앵커는 구조 기반 ASCII 리터럴 + Python str.replace. 행번호 사용 금지(드리프트).
- 내부 버전마커 주석 필수 (`// CONTRACT:v<버전>`) — 멱등 판정 기준.
  id 존재만으로 멱등 판단 금지.
- dry-run → apply → grep/wc 증거 출력. **완료 선언 금지, 출력만 인정.**
- 백업 자동 생성 필수.
- **JS 본체: node --check 필수 (치환본/실파일 이중)**
- **HTML: .html 파일에 node --check 직접 실행 금지** — HTML은 grep, mount count,
  브라우저 렌더로 검증한다. (근거: GLOBAL-BUMP 중 .html에 node --check를 실행해
  중단, 첫 파일만 부분 적용 → resume 패치로 보정한 사고. 원자성 원칙 위반 사례.)
- Python 생성기: py_compile 필수 (치환본/실파일 이중)
- 바이트 수는 버전 힌트일 뿐 기능 검증 아님. wc -c 사용 (python len()은 문자 수).
- 서로 다른 패치 동시 배포 금지. 단, 동일 파일 내 관련 갭 묶음은 허용.

## 9. 계약 이력

- **v무마커 (~20260708c)**: header/footer/4언어/NAV6. contact 없음, 페이지 통보 없음.
- **v20260709a**: B4 contact(CONTACT_LABEL+contactHTML) + B5 f29:lang 이벤트.
  배포 2026-07-09 04:34 UTC, 8,845→9,374 bytes, 증거 grep 5종 실증.
- **v20260709b**: B6 copyright(COPYRIGHT[LANG] 4언어 3줄 + f29-foot-copy +
  applyLang 재렌더) + foot-dis/foot-copy keep-all 개행 규약.
  참조 3파일(index/pro/portal) 버전쿼리 동시 bump 실증.
- **v20260709b 후속 — STOCK-FACTORY-CONTRACT-SYNC** (2026-07-09):
  /var/www/f29-stock/{code}/(306개, 생성기 build_stock_pages.py)가 계약 미준수
  (v20260708c 고정, 자체 nav/disc 하드코딩)로 감사 중 발견됨.
  패치 P1~P5: 버전 동기화 + 자체 nav 제거 + 자체 disc 제거 + 종목 특화
  컴플라이언스 문구("특정 종목의 매수·매도 추천이 아닙니다")를 본문 .judg 카드로
  이동(안 B) — footer SSOT와 종목별 본문 방어 문구의 분리 원칙 확립.
  306개 재생성, grep 4종 + 렌더 실증(005930/000660/009150).
- **v20260709b 후속 — STOCK-FACTORY-MOBILE-VISUAL-FIX** (2026-07-09):
  우측 X축 라벨 text-anchor="end", Y축 중간값 색 #5C6B84→#6F8098,
  dead CSS(.navlinks/.disc)·미사용 nav_links 변수 제거. 306개 재생성 실증.
- **v20260709b 후속 — PRO-GATE-HISTORY-I18N-FIX** (2026-07-09):
  pro.html 게이트 히스토리 카드 4언어 T객체 전환(gateHist* 6키),
  한국어 하드코딩(GH_NAMES/GH_TIP) 제거. 114,450→118,353 bytes. chrome.js 무관.
- **v20260709b 후속 — GLOBAL-CHROME-REF-BUMP** (2026-07-09):
  잔존 구버전 참조 5파일(kr/weight/us/lab/match) 전부 20260709b 통일.
  사고 1건: .html에 node --check 직접 실행으로 중단·부분 적용 → resume 보정.
  §8에 HTML 검증 규약으로 명문화.
- **CONTRACT-UNIFY** (2026-07-09): 채팅 정본과 서버 신규 생성본 이원화 해소.
  U1~U8 재실측 후 이 통합본으로 단일화. /root/CHROME_CONTRACT.md 유일 정본 확정.
