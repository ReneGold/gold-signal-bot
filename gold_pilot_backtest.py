#!/usr/bin/env python3
"""Pilot-Backtest mit geschlossenen Goldkerzen; keine Orders und kein Telegram."""
import contextlib
import csv
import importlib.util
import io
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

SOURCE = Path(__file__).with_name("gold_signal_bot_v3_9_5_diagnose (2).py")
spec = importlib.util.spec_from_file_location("gold_pilot_bot", SOURCE)
bot = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bot
spec.loader.exec_module(bot)
bot.send = lambda *_: None
bot.save_state = lambda *_: None
bot.TG_TOKEN = ""
bot.TG_CHAT = ""

candles = bot.candles("15min", 320)
htf = bot.candles(bot.HTF_INTERVAL, 220)
ef, es, atr = bot.indicators(candles)
end = [i for i,c in enumerate(candles) if c.t + timedelta(minutes=15,seconds=20) <= datetime.now(timezone.utc)]
indices = end[-100:]
if len(indices) != 100 or indices[0] < 80:
    raise RuntimeError("Zu wenig abgeschlossene Kerzen")

# Konservatives Modell: Signal auf Kerzenschluss, Ausführung erst zur nächsten Kerzeneröffnung.
# Exit: TP3 oder SL; kein Teilverkauf. Wenn TP und SL in derselben Kerze: SL zuerst.
# Spread+Slippage werden als feste Belastung in Preis-Einheiten erfasst; kein Broker-PnL.
cost = float(os.getenv("ROUND_TRIP_COST_USD_PER_OZ", "0.50"))
results = []
for threshold in (60, 65, 70):
    bot.MIN_SCORE = threshold
    active = None
    for k,i in enumerate(indices):
        c = candles[i]
        if active is not None:
            # Aktive Position wird erst ab Folgekerze betrachtet.
            sign, entry, sl, tp, opened, score = active
            stopped = c.l <= sl if sign == 1 else c.h >= sl
            target = c.h >= tp if sign == 1 else c.l <= tp
            if stopped or target:
                exit_price = sl if stopped else tp
                risk = abs(entry - sl)
                pnl_r = ((exit_price-entry)*sign-cost)/risk
                results.append(dict(threshold=threshold, entry_time=opened, exit_time=c.t.isoformat(), direction="LONG" if sign==1 else "SHORT", score=score, entry=entry, sl=sl, tp3=tp, exit=exit_price, outcome="STOP" if stopped else "TP3", net_r=round(pnl_r,4)))
                active = None
            continue
        if k+1 >= len(indices):
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            s = bot.signal(candles,ef,es,atr,htf,i)
        if not s:
            continue
        next_candle = candles[indices[k+1]]
        if next_candle.t <= c.t:
            continue
        sign = s[0]
        entry = next_candle.o
        sl = s[2]
        # Stop muss auch am tatsächlichen Folgekerzen-Einstieg auf richtiger Seite liegen.
        if (entry-sl)*sign <= 0:
            continue
        risk = abs(entry-sl)
        tp = entry + sign * bot.TP3_R * risk
        active = (sign,entry,sl,tp,next_candle.t.isoformat(),s[8])
    if active:
        print("OFFEN zum Ende des Fensters, nicht gewertet:",threshold,active[5])

fields = ["threshold","entry_time","exit_time","direction","score","entry","sl","tp3","exit","outcome","net_r"]
with open("gold_pilot_backtest_trades.csv","w",newline="",encoding="utf-8") as f:
    out=csv.DictWriter(f,fieldnames=fields);out.writeheader();out.writerows(results)
print("PILOT: 100 geschlossene 15min-Kerzen; ohne TP1/TP2/Trailing, Folgkerzen-Open, SL zuerst")
print("Modellierte Preis-Kosten USD/oz je Roundtrip:",cost)
for threshold in (60,65,70):
    x=[r["net_r"] for r in results if r["threshold"]==threshold]
    print(f"Score {threshold}: abgeschlossene Trades={len(x)}, Netto-R gesamt={sum(x):.2f}, Treffer={sum(v>0 for v in x)}")
print("CSV: gold_pilot_backtest_trades.csv")
print("ACHTUNG: begrenzte Stichprobe, vereinfachte Exit-Logik und Kostenannahme: kein Nachweis der Profitabilitaet.")
