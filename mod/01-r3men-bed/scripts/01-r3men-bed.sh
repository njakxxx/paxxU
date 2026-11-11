#!/usr/bin/env bash
# Overlay-Skript für SnapmakerU1-Extended-Firmware (paxx12):
# spielt das R3men Graphite Heated Bed in die Werks-printer.cfg der Firmware ein.
# Wird von scripts/create_firmware.sh aufgerufen:  ./<overlay>/scripts/01-r3men-bed.sh "$ROOTFS_DIR"
set -eo pipefail

if [[ -z "$CREATE_FIRMWARE" ]]; then
  echo "Error: This script should be run within the create_firmware.sh environment."
  exit 1
fi

ROOTFS="${1:-$ROOTFS_DIR}"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
CFG="$ROOTFS/home/lava/origin_printer_data/config/printer.cfg"

[[ -f "$CFG" ]] || { echo "FEHLER: $CFG nicht gefunden – Firmware-Layout hat sich geändert."; exit 1; }

echo ">> R3men Graphite Bed -> $CFG"
python3 "$HERE/tools/apply_r3men_bed.py" --no-backup --strict "$CFG"

# Gegenprobe: Build schlägt fehl, wenn etwas nicht drin ist
grep -q '^\[thermistor R3men_bed\]' "$CFG"
grep -q '^sensor_type: R3men_bed' "$CFG"
grep -q '^max_temp: 120' "$CFG"
grep -q '^position_max: 265' "$CFG"
echo ">> R3men Graphite Bed eingespielt."
