#!/usr/bin/env python3
"""
F29 Recovery Core P0 — STEP 3: 외부 API 후보 실측 (표준 라이브러리 전용)
실행: python3 p0_3_probe.py   (운영자, root@vultr — 서버는 거래소 도메인 접근 가능)

확인 대상 (스펙 §2, P0 지시서 C~G):
  C 현물 taker-buy 캔들 (bar_taker_aggregate PASS/FAIL 판정)
  D 파생 OI·funding·mark·index
  E 가격 SSOT (BTC/ETH 4h·1d, 730일 백필 가능성)
  G breadth 8종 후보 유동성·결측

산출:
  P0_SOURCE_PROBE.json      후보별 필드 유무·rate limit 헤더·timestamp 정합
  P0_SPOT_KLINE_FIXTURE.json
  P0_DERIVATIVES_FIXTURE.json
  P0_BREADTH_CANDIDATE.json

원칙: production 무접촉. fixture는 /root/f29-recovery-core-p0/ 에만. 원시 대량 저장 없음(샘플 수 개 행만).
robots·login·CAPTCHA 우회 없음. rate limit 헤더를 읽어 기록만 한다.
"""
import json
import os
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone

OUT = "/root/f29-recovery-core-p0"
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "F29-Core-P0/1.0 (probe; contact jonborica)"}
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url, timeout=12):
    """GET → (status, headers dict, parsed json | text). 예외는 error 문자열로."""
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
            hdr = {k.lower(): v for k, v in r.headers.items()}
            try:
                return r.status, hdr, json.loads(body)
            except json.JSONDecodeError:
                return r.status, hdr, body[:500]
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in (e.headers or {}).items()}, f"HTTPError {e.code}"
    except Exception as e:
        return None, {}, f"{type(e).__name__}: {str(e)[:120]}"


def rate_headers(hdr):
    """rate limit 관련 헤더만 추출."""
    keys = [k for k in hdr if any(t in k for t in
            ("rate", "limit", "retry", "weight", "used", "remaining"))]
    return {k: hdr[k] for k in keys}


probe = {"probed_at": NOW, "candidates": {}}


# ── C. 현물 taker-buy 캔들 ────────────────────────────────────────────
# Binance klines: 배열 인덱스 5=volume(base), 9=taker buy base volume, 6=close time
def probe_binance_spot():
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=3"
    st, hdr, js = get(url)
    r = {"endpoint": url, "status": st, "rate_headers": rate_headers(hdr)}
    ok = False
    if st == 200 and isinstance(js, list) and js:
        row = js[-1]
        # Binance kline: [openTime, o,h,l,c, volume, closeTime, quoteVol, trades, takerBuyBase, takerBuyQuote, ignore]
        try:
            total_base = float(row[5]); taker_buy_base = float(row[9]); close_time = int(row[6])
            bar_delta = 2 * taker_buy_base - total_base
            ok = True
            r.update({
                "has_total_base_volume": True,
                "has_taker_buy_base_volume": True,
                "has_close_time": True,
                "sample": {"close_time_ms": close_time, "total_base": total_base,
                           "taker_buy_base": taker_buy_base, "bar_delta": round(bar_delta, 4)},
            })
        except (IndexError, ValueError, TypeError) as e:
            r["parse_error"] = str(e)
    r["bar_taker_aggregate"] = "pass" if ok else "fail"
    return r, (js if st == 200 else None)


# ── D. 파생 OI·funding·mark·index ────────────────────────────────────
def probe_binance_futures():
    res = {}
    # premiumIndex: markPrice, indexPrice, lastFundingRate
    st, hdr, js = get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT")
    res["premiumIndex"] = {"status": st, "rate_headers": rate_headers(hdr)}
    if st == 200 and isinstance(js, dict):
        res["premiumIndex"].update({
            "has_mark": "markPrice" in js, "has_index": "indexPrice" in js,
            "has_funding": "lastFundingRate" in js,
            "sample": {k: js.get(k) for k in ("markPrice", "indexPrice", "lastFundingRate", "time")},
        })
    # openInterest
    st2, hdr2, js2 = get("https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT")
    res["openInterest"] = {"status": st2, "rate_headers": rate_headers(hdr2)}
    if st2 == 200 and isinstance(js2, dict):
        res["openInterest"].update({"has_oi": "openInterest" in js2,
                                    "sample": {k: js2.get(k) for k in ("openInterest", "time")}})
    # funding history (30일 분위수 백필 가능성)
    st3, hdr3, js3 = get("https://fapi.binance.com/fapi/v1/fundingRate?symbol=BTCUSDT&limit=3")
    res["fundingRate_history"] = {"status": st3, "backfill_ok": st3 == 200 and isinstance(js3, list) and len(js3) > 0}
    return res, (js if st == 200 else None)


# ── E. 가격 SSOT (730일 백필 가능성) ─────────────────────────────────
def probe_price_backfill():
    # 1d klines limit=1000 → 약 2.7년, 730일 백필 충분
    url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&limit=1000"
    st, hdr, js = get(url)
    r = {"endpoint": url, "status": st, "rate_headers": rate_headers(hdr)}
    if st == 200 and isinstance(js, list):
        r.update({"rows_returned": len(js), "backfill_730d_ok": len(js) >= 730,
                  "oldest_open_ms": js[0][0] if js else None,
                  "newest_open_ms": js[-1][0] if js else None})
    # ETH 4h 존재 확인
    st2, _, js2 = get("https://api.binance.com/api/v3/klines?symbol=ETHUSDT&interval=4h&limit=2")
    r["eth_4h_ok"] = st2 == 200 and isinstance(js2, list) and len(js2) >= 1
    return r


# ── G. breadth 8종 후보 유동성·결측 ──────────────────────────────────
# 후보: 스테이블·래핑·레버리지 제외한 고유동성 비스테이블 (P0에서 실측 후 잠금)
BREADTH_CANDIDATES = ["ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
                      "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOGEUSDT"]


def probe_breadth():
    rows = []
    for sym in BREADTH_CANDIDATES:
        url = f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1d&limit=60"
        st, _, js = get(url)
        if st == 200 and isinstance(js, list) and js:
            quote_vol = sum(float(row[7]) for row in js) / len(js)  # 평균 일 거래대금(quote)
            rows.append({"symbol": sym, "status": 200, "bars": len(js),
                         "avg_daily_quote_vol": round(quote_vol, 0),
                         "missing": 60 - len(js)})
        else:
            rows.append({"symbol": sym, "status": st, "bars": 0, "avg_daily_quote_vol": 0, "missing": 60})
        time.sleep(0.2)  # 예의상 간격
    rows.sort(key=lambda x: x["avg_daily_quote_vol"], reverse=True)
    return rows


# ── 실행 ─────────────────────────────────────────────────────────────
print("=== C. 현물 taker-buy 캔들 ===")
spot_r, spot_fixture = probe_binance_spot()
probe["candidates"]["binance_spot_5m"] = spot_r
print(json.dumps(spot_r, ensure_ascii=False, indent=2))

print("\n=== D. 파생 ===")
deriv_r, deriv_fixture = probe_binance_futures()
probe["candidates"]["binance_futures"] = deriv_r
print(json.dumps(deriv_r, ensure_ascii=False, indent=2))

print("\n=== E. 가격 백필 ===")
price_r = probe_price_backfill()
probe["candidates"]["binance_price_backfill"] = price_r
print(json.dumps(price_r, ensure_ascii=False, indent=2))

print("\n=== G. breadth 8종 ===")
breadth_rows = probe_breadth()
for row in breadth_rows:
    print(f"  {row['symbol']:10} bars={row['bars']:3} missing={row['missing']:2} "
          f"avg_quote_vol={row['avg_daily_quote_vol']:,.0f} status={row['status']}")

# 산출물 기록
with open(f"{OUT}/P0_SOURCE_PROBE.json", "w", encoding="utf-8") as f:
    json.dump(probe, f, ensure_ascii=False, indent=2)

if spot_fixture:
    with open(f"{OUT}/P0_SPOT_KLINE_FIXTURE.json", "w", encoding="utf-8") as f:
        json.dump({"source": "binance_spot_5m", "captured_at": NOW,
                   "note": "필드 순서 검증용 3행 샘플. 원시 체결 아님(집계 캔들).",
                   "rows": spot_fixture}, f, ensure_ascii=False, indent=2)

if deriv_fixture:
    with open(f"{OUT}/P0_DERIVATIVES_FIXTURE.json", "w", encoding="utf-8") as f:
        json.dump({"source": "binance_futures", "captured_at": NOW,
                   "premiumIndex_sample": deriv_fixture}, f, ensure_ascii=False, indent=2)

breadth_locked = [r["symbol"] for r in breadth_rows if r["bars"] >= 55 and r["avg_daily_quote_vol"] > 0][:8]
with open(f"{OUT}/P0_BREADTH_CANDIDATE.json", "w", encoding="utf-8") as f:
    json.dump({"version": "core-breadth-v1-candidate", "probed_at": NOW,
               "symbols": breadth_locked,
               "excluded": [r["symbol"] for r in breadth_rows if r["symbol"] not in breadth_locked],
               "detail": breadth_rows}, f, ensure_ascii=False, indent=2)

# 요약 판정
print("\n=== P0 자동 판정 요약 ===")
c_pass = spot_r.get("bar_taker_aggregate") == "pass"
d_pass = deriv_r.get("openInterest", {}).get("has_oi") and \
    deriv_r.get("premiumIndex", {}).get("has_funding")
e_pass = price_r.get("backfill_730d_ok")
g_pass = len(breadth_locked) >= 8
print(f"  C taker-buy 완전집계: {'PASS' if c_pass else 'FAIL'}")
print(f"  D 파생 OI+funding+mark+index: {'PASS' if d_pass else 'FAIL'}")
print(f"  E 730일 백필: {'PASS' if e_pass else 'FAIL'}")
print(f"  G breadth 8종 잠금: {'PASS' if g_pass else 'FAIL'} ({breadth_locked})")
print(f"\n산출물: {OUT}/P0_SOURCE_PROBE.json 등 4종")
