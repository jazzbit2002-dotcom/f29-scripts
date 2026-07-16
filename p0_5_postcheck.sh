#!/usr/bin/env bash
# F29 Recovery Core P0 — STEP 5: 무접촉 증명(SHA 전후 대조) + 증거 조립
# 실행: bash p0_5_postcheck.sh   (STEP 1~4 모두 실행 후 마지막)
set -u
OUT=/root/f29-recovery-core-p0
SHA0="$OUT/P0_SHA_BASELINE.txt"
SHA1="$OUT/P0_SHA_POSTCHECK.txt"
EV="$OUT/P0_EVIDENCE.md"

# 종료 시점 SHA 재측정 (STEP1과 동일 대상)
{
  echo "=== SHA postcheck (P0 종료) @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  for f in \
    /root/f29/server.js \
    /root/f29/state.json \
    /root/f29-recovery/ledger/state.json \
    /etc/nginx/sites-enabled/f29 \
    /var/www/f29-shared/f29-chrome.js ; do
    if [ -f "$f" ]; then echo "$(sha256sum "$f")"; else echo "ABSENT  $f"; fi
  done
} > "$SHA1" 2>&1

echo "=== 무접촉 검증 (baseline vs postcheck) ==="
if diff -q "$SHA0" <(grep -v '^===' "$SHA1") >/dev/null 2>&1 || \
   diff <(grep -v '^===' "$SHA0") <(grep -v '^===' "$SHA1") >/dev/null 2>&1; then
  UNTOUCHED="PASS — 기존 서비스 SHA 전후 일치"
else
  UNTOUCHED="CHECK — 차이 발견 (아래 diff 확인)"
fi
echo "$UNTOUCHED"
diff <(grep -v '^===' "$SHA0") <(grep -v '^===' "$SHA1") || true

# 증거 문서 조립
{
  echo "# F29 Recovery Core — P0 증거"
  echo ""
  echo "생성: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo ""
  echo "## 무접촉 검증"
  echo "$UNTOUCHED"
  echo ""
  echo "## 산출물 목록"
  ls -la "$OUT" | sed 's/^/    /'
  echo ""
  echo "## 자동 판정 (p0_3_probe.py 요약 재출력)"
  if [ -f "$OUT/P0_SOURCE_PROBE.json" ]; then
    python3 - "$OUT/P0_SOURCE_PROBE.json" << 'PYEOF'
import json, sys
p = json.load(open(sys.argv[1]))
c = p["candidates"]
def g(path, d=None):
    cur = c
    for k in path: cur = cur.get(k, {}) if isinstance(cur, dict) else {}
    return cur if cur != {} else d
print("  C taker-buy:", c.get("binance_spot_5m", {}).get("bar_taker_aggregate"))
oi = c.get("binance_futures", {}).get("openInterest", {}).get("has_oi")
fund = c.get("binance_futures", {}).get("premiumIndex", {}).get("has_funding")
print("  D 파생 OI+funding:", "pass" if (oi and fund) else "fail")
print("  E 730d 백필:", "pass" if c.get("binance_price_backfill", {}).get("backfill_730d_ok") else "fail")
PYEOF
  fi
  echo ""
  echo "## breadth 후보"
  [ -f "$OUT/P0_BREADTH_CANDIDATE.json" ] && python3 -c "import json;d=json.load(open('$OUT/P0_BREADTH_CANDIDATE.json'));print('   locked:',d['symbols'])"
  echo ""
  echo "## ETF fixture 채움 상태 (운영자 수동 확인 필요)"
  for tk in IBIT FBTC GBTC ARKB; do
    f="$OUT/P0_ETF_FIXTURES/$tk.json"
    [ -f "$f" ] && python3 -c "import json;d=json.load(open('$f'));print(f'   $tk: parser_possible={d[\"parser_fixture_possible\"]} source={d[\"source_kind\"]}')"
  done
} > "$EV" 2>&1

echo ""
echo "STEP5 완료. 증거: $EV"
echo "----- P0_EVIDENCE.md -----"
cat "$EV"
