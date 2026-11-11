#!/usr/bin/env python3
"""Spielt die R3men-Graphite-Bed-Konfiguration in eine Klipper-cfg (Snapmaker U1) ein.

Aufruf:  python3 apply_r3men_bed.py [--no-backup] [--strict] printer.cfg   (oder printer_2.cfg)
- legt vorher eine Sicherung <datei>.bak-<zeitstempel> an
- fügt [thermistor R3men_bed] direkt über [heater_bed] ein (bzw. ersetzt ihn)
- ersetzt die komplette [heater_bed]-Sektion
- setzt in [stepper_z] position_endstop und position_max auf 265
Mehrfaches Ausführen ist unschädlich (idempotent).
"""
import re
import shutil
import sys
import time

THERMISTOR = """[thermistor R3men_bed]
temperature1: 25
resistance1: 100000
temperature2: 97
resistance2: 1385
temperature3: 248
resistance3: 165
"""

HEATER_BED = """[heater_bed]
heater_pin: PE9
sensor_type: R3men_bed
sensor_pin: PC2
allow_pid_calibrate: False
ignore_pid_json: True
control: pid
pid_Kp: 33.651
pid_Ki: 0.975
pid_Kd: 290.238
full_power_threshold: 20.0
zero_power_threshold: 0.45
pid2_pid_Kp: 35.602
pid2_pid_Ki: 0.734
pid2_pid_Kd: 431.674
pid2_full_power_threshold: 20.0
pid2_zero_power_threshold: 0.5
pid2_settle_delta: 1.5
pwm_cycle_time: 1
report_time_delta: 1
settle_delta: 1.5
smooth_time: 4.5
min_temp: 0
max_temp: 120
min_temp_overshoot: 10
max_temp_overshoot: 10
"""

Z_MAX = "265"
SECTION_RE = re.compile(r"^\[([^\]]+)\]\s*(#.*)?$")


def find_section(lines, name):
    """Liefert (start, ende) der Sektion; Ende = nächste Sektion / SAVE_CONFIG-Block."""
    start = None
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line.strip())
        if start is None:
            if m and m.group(1).strip() == name:
                start = i
        elif m or line.startswith("#*#"):
            end = i
            # Leer-/Kommentarzeilen vor der nächsten Sektion gehören zu dieser
            while end > start + 1 and (not lines[end - 1].strip() or lines[end - 1].lstrip().startswith("#")):
                end -= 1
            return start, end
    if start is None:
        return None
    end = len(lines)
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    return start, end


def main(path, backup=True, strict=False):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    # 1) alten R3men-Thermistor entfernen (falls schon vorhanden)
    sec = find_section(lines, "thermistor R3men_bed")
    if sec:
        del lines[sec[0]:sec[1]]
        while sec[0] < len(lines) and not lines[sec[0]].strip():
            del lines[sec[0]]

    # 2) [heater_bed] ersetzen + Thermistor davor setzen
    sec = find_section(lines, "heater_bed")
    if not sec:
        sys.exit(f"FEHLER: keine [heater_bed]-Sektion in {path} – falsche Datei?")
    block = (THERMISTOR + "\n" + HEATER_BED).splitlines(keepends=True)
    lines[sec[0]:sec[1]] = block

    # 3) [stepper_z] anpassen
    sec = find_section(lines, "stepper_z")
    if not sec:
        if strict:
            sys.exit(f"FEHLER: keine [stepper_z]-Sektion in {path}.")
        print(f"WARNUNG: keine [stepper_z]-Sektion in {path} – Z-Werte NICHT geändert.")
    else:
        found = set()
        for i in range(sec[0] + 1, sec[1]):
            m = re.match(r"^(position_endstop|position_max)\s*[:=]", lines[i])
            if m:
                lines[i] = f"{m.group(1)}: {Z_MAX}\n"
                found.add(m.group(1))
        missing = [k for k in ("position_endstop", "position_max") if k not in found]
        for k in missing:
            lines.insert(sec[0] + 1, f"{k}: {Z_MAX}\n")

    if any(l.startswith("#*# [heater_bed]") for l in lines):
        msg = ("Im SAVE_CONFIG-Block (#*#) steht ein [heater_bed] mit alten PID-Werten – "
               "der überschreibt die neuen Werte.")
        if strict:
            sys.exit("FEHLER: " + msg)
        print("ACHTUNG: " + msg + " Diese #*#-Zeilen bitte löschen.")

    if backup:
        bak = f"{path}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
        shutil.copy2(path, bak)
    # Dateirechte/Eigentümer bleiben erhalten, weil die Datei in-place überschrieben wird
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"OK: {path} angepasst" + (f", Sicherung: {bak}" if backup else ""))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="R3men Graphite Bed in Klipper-cfg einspielen (Snapmaker U1)")
    ap.add_argument("cfg", help="printer.cfg bzw. printer_2.cfg")
    ap.add_argument("--no-backup", action="store_true", help="keine .bak-Datei anlegen (für Firmware-Build)")
    ap.add_argument("--strict", action="store_true", help="bei jeder Unstimmigkeit abbrechen (für Firmware-Build)")
    a = ap.parse_args()
    main(a.cfg, backup=not a.no_backup, strict=a.strict)
