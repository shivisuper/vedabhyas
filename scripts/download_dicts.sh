#!/usr/bin/env bash
# Download Monier-Williams and Apte XML from the CDSL csl-orig repository.
#
# Files land in ~/.local/share/vedabhyas/ — the default location that
# `vedabhyas ingest` checks automatically.
#
# Usage:
#   bash scripts/download_dicts.sh           # download both
#   bash scripts/download_dicts.sh --mw      # MW only
#   bash scripts/download_dicts.sh --apte    # Apte only

set -euo pipefail

DEST_DIR="${HOME}/.local/share/vedabhyas"
BASE_URL="https://raw.githubusercontent.com/sanskrit-lexicon/csl-orig/master/v02"

MW_URL="${BASE_URL}/mw/mw.xml"
APTE_URL="${BASE_URL}/ap90/ap90.xml"

DO_MW=true
DO_APTE=true

for arg in "$@"; do
  case "$arg" in
    --mw)   DO_APTE=false ;;
    --apte) DO_MW=false ;;
    *)
      echo "Unknown flag: $arg" >&2
      echo "Usage: $0 [--mw | --apte]" >&2
      exit 1
      ;;
  esac
done

# Prefer curl; fall back to wget
if command -v curl &>/dev/null; then
  download() { curl -L --progress-bar -o "$2" "$1"; }
elif command -v wget &>/dev/null; then
  download() { wget -O "$2" "$1"; }
else
  echo "Error: neither curl nor wget found." >&2
  exit 1
fi

mkdir -p "$DEST_DIR"

if $DO_MW; then
  MW_DEST="${DEST_DIR}/mw.xml"
  if [[ -f "$MW_DEST" ]]; then
    echo "mw.xml already present at ${MW_DEST} — skipping (delete to re-download)."
  else
    echo "Downloading Monier-Williams XML…"
    download "$MW_URL" "$MW_DEST"
    echo "  → ${MW_DEST}"
  fi
fi

if $DO_APTE; then
  APTE_DEST="${DEST_DIR}/apte.xml"
  if [[ -f "$APTE_DEST" ]]; then
    echo "apte.xml already present at ${APTE_DEST} — skipping (delete to re-download)."
  else
    echo "Downloading Apte (AP90) XML…"
    download "$APTE_URL" "$APTE_DEST"
    echo "  → ${APTE_DEST}"
  fi
fi

echo ""
echo "Done. Run the ingestion pipeline next:"
echo "  vedabhyas ingest"
echo ""
echo "Or, if running from source:"
echo "  python -m vedabhyas ingest"
