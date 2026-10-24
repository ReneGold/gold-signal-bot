#!/usr/bin/env python3
"""Persistent research ledger: records B/C observations and simulated outcomes. No orders."""
import csv,importlib.util,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
def read(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def write(path,rows,fields):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
snap=read(P/"gold_forward_bc_snapshot.csv")
history=P/"gold_forward_bc_history.csv"
old=read(history);data={r["signal_candle_utc"]:r for r in old}
for r in snap:data.setdefault(r["signal_candle_utc"],r)
snap_fields=list(snap[0]) if snap else list(old[0]) if old else []
if snap_fields:write(history,[data[k] for k in sorted(data)],snap_fields)
ledger=P/"gold_forward_bc_paper_trades.csv"
existing=read(ledger)
fields=["id","variant","signal_candle_utc","side","score","entry_time_utc","entry","initial_sl","tp1","tp2","tp3","stage","exit_time_utc","exit","status","net_R","notes"]
positions={r["id"]:r for r in existing}
# Import complete recent 15-minute candles, without seeing into the future.
source=P/"gold_signal_bot_v3_9_5_diagnose (2).py"
spec=importlib.util.spec_from_file_location("paper_data_only",source)
bot=importlib.util.module_from_spec(spec);sys.modules[spec.name]=bot;spec.loader.exec_module(bot)
candles=bot.candles("15min",320)
by_time={c.t.isoformat():c for c in candles}
times=sorted(by_time)
def val(s):return float(s)
for r in [data[k] for k in sorted(data)]:
    if r["side"]=="NONE":continue
    for variant,col in (("B","b_accepted"),("C","c_accepted")):
        if str(r[col])!="1":continue
        key=variant+"|"+r["signal_candle_utc"]
        if key in positions:continue
        expected=datetime.fromisoformat(r["signal_candle_utc"])+timedelta(minutes=15)
        positions[key]=dict(id=key,variant=variant,signal_candle_utc=r["signal_candle_utc"],side=r["side"],score=r["score"],entry_time_utc=expected.isoformat(),entry="",initial_sl=r["stop"],tp1=r["tp1"],tp2=r["tp2"],tp3=r["tp3"],stage="0",exit_time_utc="",exit="",status="AWAIT_ENTRY",net_R="",notes="indicative 15m OHLC only; no real broker execution")
for position in positions.values():
    if position["status"]=="CLOSED":continue
    entry_time=position["entry_time_utc"]
    if position["status"]=="AWAIT_ENTRY":
        bar=by_time.get(entry_time)
        if bar is None:continue
        position["entry"]=str(bar.o)
        position["status"]="OPEN"
        # Preserve original stop and targets based on signal close for transparent comparability.
    if position["status"]!="OPEN":continue
    sign=1 if position["side"]=="LONG" else -1
    entry=val(position["entry"]);sl=val(position["initial_sl"])
    risk=(entry-sl)*sign
    if risk<=0:
        position["status"]="INVALID";position["notes"]="non-positive initial risk after next bar open gap";continue
    stage=int(position["stage"])
    for ts in times:
        if ts<entry_time:continue
        bar=by_time[ts]
        protect=val(position["tp1"]) if stage>=2 else entry if stage>=1 else sl
        gap=(bar.o<=protect if sign==1 else bar.o>=protect)
        touched_stop=(bar.l<=protect if sign==1 else bar.h>=protect)
        hit3=(bar.h>=val(position["tp3"]) if sign==1 else bar.l<=val(position["tp3"]))
        hit2=(bar.h>=val(position["tp2"]) if sign==1 else bar.l<=val(position["tp2"]))
        hit1=(bar.h>=val(position["tp1"]) if sign==1 else bar.l<=val(position["tp1"]))
        if touched_stop or hit3:
            price=(bar.o if gap else protect) if touched_stop else val(position["tp3"])
            position.update(status="CLOSED",exit_time_utc=ts,exit=str(price),
                net_R=str(round(((price-entry)*sign-0.5)/risk,5)),
                notes="GAP_STOP" if gap and touched_stop else "STOP" if touched_stop else "TP3")
            break
        if hit2:stage=2
        elif hit1:stage=max(stage,1)
    position["stage"]=str(stage)
write(ledger,[positions[k] for k in sorted(positions)],fields)
print(f"Historical observation rows={len(data)} unique; paper trades={len(positions)} closed={sum(r['status']=='CLOSED' for r in positions.values())} open={sum(r['status']=='OPEN' for r in positions.values())}")
print("CAVEAT: rough paper OHLC model; limited 320-bar price lookback, non-broker prices, target order ambiguous, synthetic cost 0.5 USD/oz.")
