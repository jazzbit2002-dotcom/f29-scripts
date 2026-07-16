# F29 Recovery Core P0 — 운영자 실행 순서

전제: root@vultr. **아무것도 수정하지 않는 실측 차수.** production·cron·nginx·server.js 무접촉.
반입: 이 5개 파일을 GitHub raw → curl 로 `/root/f29-recovery-core-p0/` 에 받거나, scp.
Python 표준 라이브러리만 사용 — pip 설치 불필요.

## 실행 (한 줄씩, 순서대로)

```
# 0) 파일 위치
mkdir -p /root/f29-recovery-core-p0 && cd /root/f29-recovery-core-p0
#    (여기에 p0_1~p0_5 5개 파일을 둔다)

# 1) 서버 baseline + SHA (무접촉 시작점)
bash p0_1_baseline.sh

# 2) namespace 충돌 검사
bash p0_2_namespace.sh

# 3) 외부 API 후보 실측 (핵심 — taker-buy/파생/백필/breadth)
python3 p0_3_probe.py

# 4) ETF 체크리스트 + 권리 원장 초안
python3 p0_4_etf_rights.py
#    → 출력된 4개 URL 접속해 P0_ETF_FIXTURES/{IBIT,FBTC,GBTC,ARKB}.json 을
#      실제 필드 유무로 채운다 (최소 2종 parser_fixture_possible=true 목표)

# 5) 무접촉 증명(SHA 전후 대조) + 증거 조립
bash p0_5_postcheck.sh
```

## 회신 방법

STEP3 과 STEP5 의 콘솔 출력 전체를 붙여넣으면 된다. 특히:
- `p0_3_probe.py` 의 "P0 자동 판정 요약"
- `p0_5_postcheck.sh` 의 "무접촉 검증" 결과 + P0_EVIDENCE.md

민감정보 없음(스크립트가 HOOK_SECRET 은 마스킹). ETF 페이지 확인 결과(필드 유무·robots)만 한 줄씩 알려주면 내가 fixture 를 마저 채운다.

## 주의

- 거래소 도메인이 서버에서 막혀 있으면 STEP3 이 실패한다 → 그 경우 어느 도메인이 막혔는지 회신(방화벽/egress 확인).
- `bar_taker_aggregate=fail` 이면 폴백(체결 표본) 경로로 전환 — 스펙 §2.2 폴백. 그래도 P0 는 진행 가능.
- ETF 4종 중 2종만 돼도 PASS. 나머지는 P2 에서 보완.
- **PASS 전 P1 코드 패치 시작 금지** (지시서 §6).
