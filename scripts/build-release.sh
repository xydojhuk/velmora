#!/usr/bin/env bash
# Pack only the current committed Git tree; never ZIP the working directory.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash scripts/release-check.sh
command -v zip >/dev/null || { echo 'Missing zip' >&2; exit 1; }
command -v sha256sum >/dev/null || { echo 'Missing sha256sum' >&2; exit 1; }

VERSION="$(tr -d '\r\n' < VERSION)"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.]+)?$ ]] || { echo 'Invalid VERSION' >&2; exit 1; }
OUTPUT_DIR="${1:-$ROOT_DIR/release}"
mkdir -p "$OUTPUT_DIR"
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)"
# Outputs go outside the archive and are never tracked.
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
mkdir -p "$TMP_DIR/tree"
git archive --format=tar HEAD | tar -xf - -C "$TMP_DIR/tree"
python3 "$ROOT_DIR/scripts/verify-release-tree.py" "$TMP_DIR/tree"
# Scan the *actual archive input* too. Git-history scanning is done in release-check.
gitleaks dir --redact --exit-code 1 "$TMP_DIR/tree"
NAME="velmora-v${VERSION}.zip"
rm -f "$OUTPUT_DIR/$NAME" "$OUTPUT_DIR/$NAME.sha256"
(cd "$TMP_DIR/tree" && zip -q -r "$OUTPUT_DIR/$NAME" .)
(cd "$OUTPUT_DIR" && sha256sum "$NAME" > "$NAME.sha256")
echo "Release: $OUTPUT_DIR/$NAME"
echo "Checksum: $OUTPUT_DIR/$NAME.sha256"
