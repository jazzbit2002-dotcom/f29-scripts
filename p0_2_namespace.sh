#!/usr/bin/env bash
# F29 Recovery Core P0 — STEP 2: namespace 충돌 검사 (읽기 전용)
# production 디렉터리를 만들지 않는다. 존재 여부만 확인.
set -u
OUT=/root/f29-recovery-core-p0
mkdir -p "$OUT"
NS="$OUT/P0_NAMESPACE.txt"

{
  echo "=== namespace 충돌 검사 @ $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
  for p in \
    /root/f29-recovery-core \
    /root/f29-recovery-core-p0 \
    /var/www/f29-recovery \
    /var/www/f29/recovery ; do
    if [ -e "$p" ]; then echo "EXISTS  $p"; else echo "free    $p"; fi
  done
  echo "--- nginx에 /recovery 라우트 이미 있나 ---"
  nginx -T 2>/dev/null | grep -n "recovery" | head -10 || echo "  (없음)"
  echo "--- 라이브 /recovery/ 응답 (참고, 무변경) ---"
  curl -s -o /dev/null -w "  HTTP %{http_code}\n" https://f29.io/recovery/ 2>/dev/null || echo "  (조회 실패)"
} > "$NS" 2>&1

echo "STEP2 완료:"
cat "$NS"
