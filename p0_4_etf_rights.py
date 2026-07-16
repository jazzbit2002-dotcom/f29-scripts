#!/usr/bin/env python3
"""
F29 Recovery Core P0 — STEP 4: ETF 4종 필드 확인 + 권리 원장 초안 생성
실행: python3 p0_4_etf_rights.py   (운영자)

ETF는 운용사 페이지 구조가 다양·가변이라 자동 파싱을 P0에서 확정하지 않는다.
이 스크립트는 (a) 확인 대상 URL·필드 체크리스트를 출력하고,
(b) P0_RIGHTS_MATRIX.json 초안과 P0_ETF_FIXTURES/ 템플릿을 만든다.
운영자가 각 운용사 공개 페이지/공개 파일에서 필드 존재를 눈으로 확인해 체크리스트를 채운다.

원칙: 로그인·CAPTCHA·robots 우회 금지. 공개 페이지/공개 다운로드 파일만.
원문 전체 저장 금지 — 필요한 필드 값과 digest만.
owner_override 는 rights allowed 로 위장하지 않는다.
"""
import json
import os
from datetime import datetime, timezone

OUT = "/root/f29-recovery-core-p0"
os.makedirs(f"{OUT}/P0_ETF_FIXTURES", exist_ok=True)
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# 확인 대상 (공개 페이지 — 운영자가 접속해 필드 위치 확인)
ETF_TARGETS = {
    "IBIT": {"issuer": "BlackRock",
             "public_page": "https://www.ishares.com/us/products/333011/ishares-bitcoin-trust",
             "check": "Shares Outstanding, NAV, Bitcoin holdings, as-of date. 공개 CSV 다운로드 링크 유무."},
    "FBTC": {"issuer": "Fidelity",
             "public_page": "https://institutional.fidelity.com/app/funds-and-products/6478/fidelity-wise-origin-bitcoin-fund-fbtc.html",
             "check": "NAV, Shares Outstanding, holdings. 일별 공개 파일 유무."},
    "GBTC": {"issuer": "Grayscale",
             "public_page": "https://www.grayscale.com/funds/grayscale-bitcoin-trust",
             "check": "Shares Outstanding, NAV per share, BTC per share/holdings."},
    "ARKB": {"issuer": "ARK/21Shares",
             "public_page": "https://www.ark-funds.com/funds/arkb",
             "check": "Shares Outstanding, NAV, holdings, as-of date."},
}

print("=== ETF 4종 공개 페이지 확인 체크리스트 (운영자 수동) ===\n")
for tk, meta in ETF_TARGETS.items():
    print(f"[{tk}] {meta['issuer']}")
    print(f"   URL:   {meta['public_page']}")
    print(f"   확인:  {meta['check']}")
    print(f"   robots/login/CAPTCHA 여부, 업데이트 시각, 필드 안정성 기록\n")

# 각 ETF fixture 템플릿 (운영자가 실제 값으로 채움 — 없으면 null 유지)
for tk in ETF_TARGETS:
    tmpl = {
        "ticker": tk, "issuer": ETF_TARGETS[tk]["issuer"], "captured_at": NOW,
        "source_kind": None,          # "public_csv" | "public_html" | "unavailable"
        "fields_present": {
            "as_of_date": None, "shares_outstanding": None,
            "nav_per_share": None, "btc_holdings": None, "total_net_assets": None},
        "sample_values": {            # 운영자가 1일치 실제 값 (원문 전체 아님)
            "as_of_date": None, "shares_outstanding": None,
            "nav_per_share": None, "btc_holdings": None},
        "robots_login_captcha": None,  # true=우회 필요(=사용 불가) / false=공개접근 가능
        "update_time_et": None, "field_stability": None,
        "parser_fixture_possible": None,  # true|false
        "input_digest": None,
    }
    path = f"{OUT}/P0_ETF_FIXTURES/{tk}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(tmpl, f, ensure_ascii=False, indent=2)
    print(f"  템플릿 생성: {path}")

# 권리 원장 초안 (모든 소스) — owner_override 패턴
rights = {
    "generated_at": NOW,
    "policy": "owner_override 는 rights_status=allowed 로 위장하지 않는다. raw 공개 금지. 단계 산출 전용.",
    "sources": [
        {"source_id": "binance_spot_klines", "technical_status": "pass",
         "rights_status": "pending", "owner_override": "accepted",
         "retention_status": "pending", "kill_switch": True, "raw_publication": False,
         "notes": "집계 캔들만 사용, 원시 체결 미저장. 공개 파생 상업 이용권 서면 미확인 → owner_override."},
        {"source_id": "binance_futures", "technical_status": "pass",
         "rights_status": "pending", "owner_override": "accepted",
         "retention_status": "pending", "kill_switch": True, "raw_publication": False,
         "notes": "OI·funding·mark·index 스냅샷. 원시값 비공개."},
        {"source_id": "etf_issuer_ibit", "technical_status": "pending",
         "rights_status": "pending", "owner_override": "accepted",
         "retention_status": "pending", "kill_switch": True, "raw_publication": False,
         "notes": "운용사 공개 페이지. 발행주식수·NAV 로 자체 추정. 운용사별 수치 비공개."},
        {"source_id": "etf_issuer_fbtc", "technical_status": "pending",
         "rights_status": "pending", "owner_override": "accepted",
         "retention_status": "pending", "kill_switch": True, "raw_publication": False, "notes": ""},
        {"source_id": "etf_issuer_gbtc", "technical_status": "pending",
         "rights_status": "pending", "owner_override": "accepted",
         "retention_status": "pending", "kill_switch": True, "raw_publication": False, "notes": ""},
        {"source_id": "etf_issuer_arkb", "technical_status": "pending",
         "rights_status": "pending", "owner_override": "accepted",
         "retention_status": "pending", "kill_switch": True, "raw_publication": False, "notes": ""},
    ],
}
with open(f"{OUT}/P0_RIGHTS_MATRIX.json", "w", encoding="utf-8") as f:
    json.dump(rights, f, ensure_ascii=False, indent=2)
print(f"\n  권리 원장 초안: {OUT}/P0_RIGHTS_MATRIX.json")
print("\nSTEP4 완료. 운영자는 각 ETF 페이지를 확인해 P0_ETF_FIXTURES/*.json 을 채운다.")
print("최소 2종에서 parser_fixture_possible=true 면 PASS 기준 충족.")
