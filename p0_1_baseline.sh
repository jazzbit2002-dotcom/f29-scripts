#!/usr/bin/env bash
# F29 Recovery Core P0 — STEP 1: 서버 baseline + SHA (읽기 전용, 무접촉)
# 실행: bash p0_1_baseline.sh  (운영자, root@vultr)
# 이 스크립트는 아무것도 수정하지 않는다. 오직 read + 기록.
set -u
OUT=/root/f29-recovery-core-p0
mkdir -p "$OUT"
BASE="$OUT/P0_SERVER_BASELINE.txt"
SHA="$OUT/P0_SHA_BASELINE.txt"

{
  echo "=== F29 Core P0 baseline @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  echo "--- host ---"; hostname
  echo "--- python ---"; python3 --version 2>&1
  echo "--- disk ---"; df -h /
  echo "--- mem ---"; free -h
  echo "--- failed units ---"; systemctl --failed --no-legend 2>/dev/null | head -20
  echo "--- crontab (참고, 무변경) ---"; crontab -l 2>/dev/null | sed 's/HOOK_SECRET=[^ ]*/HOOK_SECRET=***/g' | head -40
  echo "--- nginx server_names (요약) ---"; nginx -T 2>/dev/null | grep -E "server_name|location /recovery" | head -30
  echo "--- pm2 (참고) ---"; pm2 list 2>/dev/null | head -20 || echo "pm2 n/a"
} > "$BASE" 2>&1

# 무접촉 대상 SHA baseline (전/후 대조용)
{
  echo "=== SHA baseline (P0 시작) @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  for f in \
    /root/f29/server.js \
    /root/f29/state.json \
    /root/f29-recovery/ledger/state.json \
    /etc/nginx/sites-enabled/f29 \
    /var/www/f29-shared/f29-chrome.js ; do
    if [ -f "$f" ]; then echo "$(sha256sum "$f")"; else echo "ABSENT  $f"; fi
  done
} > "$SHA" 2>&1

echo "STEP1 완료. 산출:"
echo "  $BASE"
echo "  $SHA"
echo "----- P0_SERVER_BASELINE.txt -----"
cat "$BASE"
echo "----- P0_SHA_BASELINE.txt -----"
cat "$SHA"
