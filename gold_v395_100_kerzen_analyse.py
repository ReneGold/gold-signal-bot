#!/usr/bin/env python3
"""Lesender Diagnosetest fuer 100 abgeschlossene XAU/USD-15min-Kerzen.
Keine Telegram-Nachrichten, keine Orders, keine Zustandsdatei.
"""
from __future__ import annotations
import contextlib
import csv
import importlib.util
import io
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

SOURCE = Path(__file__).with_name("gold_signal_bot_v3_9_5_diagnose (2).py")
COUNT = 100


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Diagnosedatei fehlt: {SOURCE.name}")
    spec = importlib.util.spec_from_file_location("gold_v395_diagnose_module", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Diagnosedatei konnte nicht geladen werden")
    bot = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bot
    spec.loader.exec_module(bot)
    # Zusaetzliche harte Sicherheit: niemals Telegram oder persistierten Zustand verwenden.
    bot.send = lambda msg: None
    bot.save_state = lambda state: None
    bot.TG_TOKEN = ""
    bot.TG_CHAT = ""
    if not bot.API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY fehlt")

    candles = bot.candles("15min", 320)
    hourly = bot.candles(bot.HTF_INTERVAL, 220)
    if len(candles) < 185 or len(hourly) < bot.SLOW + 5:
        raise RuntimeError(f"Zu wenige Kerzen fuer 100 Tests: 15min={len(candles)}, HTF={len(hourly)}")
    ef, es, atr = bot.indicators(candles)
    end = [i for i, candle in enumerate(candles)
           if candle.t + timedelta(minutes=15) + timedelta(seconds=20) <= datetime.now(timezone.utc)]
    indices = end[-COUNT:]
    if len(indices) != COUNT or indices[0] < 80:
        raise RuntimeError("Nicht genug historische Daten nach der Einlaufphase")

    outcomes = Counter()
    rows = []
    for i in indices:
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            signal = bot.signal(candles, ef, es, atr, hourly, i)
        output = capture.getvalue()
        score = re.search(r"\[SCORE\].*?LONG=(\d+)/100 \(Basis=(True|False)\).*?SHORT=(\d+)/100 \(Basis=(True|False)\)", output)
        long_score = int(score.group(1)) if score else None
        long_base = score.group(2) == "True" if score else False
        short_score = int(score.group(3)) if score else None
        short_base = score.group(4) == "True" if score else False
        if signal is not None:
            status = "Trade-Kandidat mit gueltigem Risiko"
        elif "Kein Einstiegsmuster" in output:
            status = "Kein Einstiegsmuster"
        elif "Stop-Abstand unzulaessig" in output:
            status = "Risikofilter / Stop-Abstand"
        elif long_base or short_base:
            if (long_score is not None and long_score < bot.MIN_SCORE and not short_base) or (short_score is not None and short_score < bot.MIN_SCORE and not long_base) or (long_score is not None and short_score is not None and max(long_score, short_score) < bot.MIN_SCORE):
                status = "Score unter Mindestwert"
            else:
                status = "Sonstiger Filter / Mehrfachbedingung"
        else:
            status = "Andere Ablehnung"
        outcomes[status] += 1
        rows.append({"kerze_utc": candles[i].t.isoformat(), "long_basis": long_base,
                     "long_score": long_score, "short_basis": short_base,
                     "short_score": short_score, "status": status,
                     "signalrichtung": ("LONG" if signal[0] == 1 else "SHORT") if signal else ""})

    print("=== GOLD DEMO V3.9.5 | 100 KERZEN | LESETEST ===")
    print("Zeitraum UTC:", rows[0]["kerze_utc"], "bis", rows[-1]["kerze_utc"])
    print("Zeitraum kann Wochenende/Handelspausen umfassen; 100 Kerzen entsprechen 25 Stunden Kerzenzeit.")
    print("Twelve Data: 15min=", len(candles), "1h=", len(hourly))
    print("Mindest-Score:", bot.MIN_SCORE)
    print("100 Kerzen untersucht:", len(rows))
    print("Kerzen mit Long-Basis:", sum(r["long_basis"] for r in rows))
    print("Kerzen mit Short-Basis:", sum(r["short_basis"] for r in rows))
    print("Kerzen mit Score >= Schwelle und Basis (LONG):", sum(r["long_basis"] and r["long_score"] is not None and r["long_score"] >= bot.MIN_SCORE for r in rows))
    print("Kerzen mit Score >= Schwelle und Basis (SHORT):", sum(r["short_basis"] and r["short_score"] is not None and r["short_score"] >= bot.MIN_SCORE for r in rows))
    for status, count in outcomes.most_common():
        print(f"  {status}: {count}")
    print("Hinweis: Signal-Kandidaten sind keine Gewinnprognose; keine SL/TP-Simulation.")
    print("Keine Telegram-Sends; keine Orders; kein state.json-Zugriff.")
    with open("gold_v395_100_kerzen_bericht.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print("CSV gespeichert: gold_v395_100_kerzen_bericht.csv")


if __name__ == "__main__":
    main()
