#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  exec sudo bash "$0" "$@"
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE=/etc/velmora/velmora.env

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Velmora is not installed."
  exit 1
fi

cd "$ROOT_DIR"

set -a
source "$ENV_FILE"
set +a

COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT_DIR/compose.yaml")
BASE="https://${DOMAIN}"
FAILED=0

ok() {
  echo "OK   $1"
}

fail() {
  echo "FAIL $1"
  FAILED=1
}

http_code() {
  curl -sS \
    --connect-timeout 5 \
    --max-time 15 \
    -o /dev/null \
    -w '%{http_code}' \
    "$1" 2>/dev/null || true
}

check_code() {
  local url="$1"
  local expected="$2"
  local code

  code="$(http_code "$url")"

  if [[ "$code" == "$expected" ]]; then
    ok "$code $url"
  else
    fail "$url returned $code instead of $expected"
  fi
}

echo "=== Containers ==="
"${COMPOSE[@]}" ps
echo

echo "=== HTTPS and HTTP ==="

check_code "$BASE/" "200"
check_code "$BASE/robots.txt" "200"
check_code "$BASE/sitemap.xml" "200"
check_code "$BASE/healthz" "200"
check_code "$BASE/login" "200"
check_code "$BASE/admin" "200"
check_code "$BASE/install" "302"
check_code "$BASE/velmora-page-that-does-not-exist" "404"

echo
echo "=== SSR home page ==="

HOME_HTML="$(curl -fsSL --max-time 15 "$BASE/" || true)"

if grep -qi '<h1' <<<"$HOME_HTML"; then
  ok "H1 is present in server-rendered HTML"
else
  fail "H1 is missing from server-rendered HTML"
fi

if grep -q 'rel="canonical"' <<<"$HOME_HTML"; then
  ok "canonical is present"
else
  fail "canonical is missing"
fi

if grep -q 'name="description"' <<<"$HOME_HTML"; then
  ok "meta description is present"
else
  fail "meta description is missing"
fi

if grep -q 'application/ld+json' <<<"$HOME_HTML"; then
  ok "JSON-LD is present"
else
  fail "JSON-LD is missing"
fi

echo
echo "=== Sitemap ==="

SITEMAP="$(curl -fsSL --max-time 15 "$BASE/sitemap.xml" || true)"

if grep -q '<urlset' <<<"$SITEMAP"; then
  ok "sitemap XML is served correctly"
else
  fail "sitemap XML was not found"
fi

if grep -Fq "<loc>${BASE}/</loc>" <<<"$SITEMAP"; then
  ok "home page is present in sitemap"
else
  fail "home page is missing from sitemap"
fi

PRODUCT_URL="$(
  grep -oE '<loc>https?://[^<]+/product/[^<]+</loc>' <<<"$SITEMAP" \
    | head -n 1 \
    | sed -E 's#</?loc>##g' \
    || true
)"

if [[ -n "$PRODUCT_URL" ]]; then
  echo
  echo "=== SSR product page ==="

  PRODUCT_HTML="$(curl -fsSL --max-time 15 "$PRODUCT_URL" || true)"

  if grep -qi '<h1' <<<"$PRODUCT_HTML"; then
    ok "Product H1 is present in server-rendered HTML"
  else
    fail "Product H1 is missing from server-rendered HTML"
  fi

  if grep -q 'rel="canonical"' <<<"$PRODUCT_HTML"; then
    ok "Product canonical is present"
  else
    fail "Product canonical is missing"
  fi

  if grep -q 'name="description"' <<<"$PRODUCT_HTML"; then
    ok "Product description is present"
  else
    fail "Product description is missing"
  fi

  if grep -q 'application/ld+json' <<<"$PRODUCT_HTML" \
    && grep -q '"Product"' <<<"$PRODUCT_HTML"; then
    ok "Product JSON-LD is present"
  else
    fail "Product JSON-LD is missing"
  fi

  PRODUCT_SLUG="${PRODUCT_URL##*/}"

  CHECKOUT_HEADERS="$(
    curl -sSI --max-time 15 "$BASE/checkout/$PRODUCT_SLUG" || true
  )"

  if grep -qi '^x-robots-tag:.*noindex' <<<"$CHECKOUT_HEADERS"; then
    ok "Checkout has X-Robots-Tag noindex"
  else
    fail "Checkout is missing X-Robots-Tag noindex"
  fi
else
  fail "No active product page was found in the sitemap"
fi

echo
echo "=== robots.txt ==="

ROBOTS="$(curl -fsSL --max-time 15 "$BASE/robots.txt" || true)"

if grep -Fqi "Sitemap: ${BASE}/sitemap.xml" <<<"$ROBOTS"; then
  ok "robots.txt contains the sitemap"
else
  fail "robots.txt does not contain the expected sitemap"
fi

echo
echo "=== Noindex pages ==="

for path in "/admin" "/login"; do
  HEADERS="$(curl -sSI --max-time 15 "$BASE$path" || true)"

  if grep -qi '^x-robots-tag:.*noindex' <<<"$HEADERS"; then
    ok "$path has X-Robots-Tag noindex"
  else
    fail "$path is missing X-Robots-Tag noindex"
  fi
done

NOT_FOUND_HEADERS="$(
  curl -sSI --max-time 15 "$BASE/velmora-page-that-does-not-exist" || true
)"

if grep -qi '^x-robots-tag:.*noindex' <<<"$NOT_FOUND_HEADERS"; then
  ok "404 has X-Robots-Tag noindex"
else
  fail "404 is missing X-Robots-Tag noindex"
fi

echo
echo "=== Installer lock ==="

INSTALL_STATUS="$(curl -fsSL --max-time 15 "$BASE/api/v1/install/status" || true)"
if grep -q '"installed":true' <<<"$INSTALL_STATUS"; then
  ok "browser installer is permanently locked"
else
  fail "browser installer does not report installed=true"
fi

echo
echo "=== Security headers ==="

HEADERS="$(curl -sSI --max-time 15 "$BASE/" || true)"

for header in \
  'strict-transport-security:' \
  'content-security-policy:' \
  'x-content-type-options:' \
  'x-frame-options:' \
  'referrer-policy:' \
  'permissions-policy:'
do
  if grep -qi "^${header}" <<<"$HEADERS"; then
    ok "$header"
  else
    fail "$header is missing"
  fi
done

echo
echo "=== Internal port exposure ==="

PUBLISHED="$("${COMPOSE[@]}" ps --format json 2>/dev/null || true)"

if grep -qE '"PublishedPort":(5432|8000|5173)' <<<"$PUBLISHED"; then
  fail "5432, 8000 or 5173 are exposed publicly"
else
  ok "5432, 8000 and 5173 are not exposed publicly"
fi

echo

if [[ "$FAILED" -ne 0 ]]; then
  echo "Checks finished with errors."
  exit 1
fi

echo "All main production checks passed."