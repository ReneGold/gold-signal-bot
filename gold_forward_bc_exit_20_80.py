#!/usr/bin/env python3
"""Separate, persistent 20/80 paper-exit shadow ledger for B/C Gold signals.
No orders, no Telegram, no changes to existing reference exit ledger.
Uses only completed 15m OHLC and conservative stop-first intrabar ordering.
Missing history freezes a trade as DATA_GAP; never silently skips prices.
"""
import csv
import importlib.util
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DEST=ROOT/"gold_forward_bc_exit_20_80.csv"
SNAP=ROOT/"gold_forward_bc_snapshot.csv"
FIELDS=("id","variant","signal_candle_utc","side","score","entry_time_utc",
        "entry","stop","tp1","tp3","stage","remaining","gross_R",
        "last_checked_utc","exit_time_utc","net_R","status","events")
COST_PER_OZ=0.50

def read_csv(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def write_csv(path,records):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        w.writeheader()
        w.writerows([{k:r.get(k,"") for k in FIELDS} for r in records])

def add_signals(positions,snapshots):
    for r in snapshots:
        if r["side"] not in ("LONG","SHORT"):continue
        for variant,accepted in (("B","b_accepted"),("C","c_accepted")):
            if str(r.get(accepted))!="1":continue
            key=variant+"|"+r["signal_candle_utc"]
            if key in positions:continue
            t=datetime.fromisoformat(r["signal_candle_utc"])+timedelta(minutes=15)
            positions[key]=dict(id=key,variant=variant,signal_candle_utc=r["signal_candle_utc"],
                side=r["side"],score=r["score"],entry_time_utc=t.isoformat(),
                entry="",stop=str(r["stop"]),tp1="",tp3="",stage="0",
                remaining="1.0",gross_R="0",last_checked_utc="",exit_time_utc="",
                net_R="",status="AWAIT_ENTRY",events="")
    return positions

def update(positions,candles,now_utc):
    # Candle timestamp is its OPEN; never analyze a still-forming candle.
    bars={b.t.isoformat():b for b in candles if b.t+timedelta(minutes=15)<=now_utc}
    ts=sorted(bars)
    if not ts:return positions
    oldest=ts[0]
    for p in positions.values():
        if p["status"] not in ("AWAIT_ENTRY","OPEN"):continue
        start=p["entry_time_utc"]
        if p["status"]=="AWAIT_ENTRY":
            if start<oldest:
                p["status"]="UNOBSERVED_ENTRY";p["events"]="ENTRY_BAR_NO_LONGER_AVAILABLE"
                continue
            if start not in bars:continue
            entry=float(bars[start].o);stop=float(p["stop"])
            direction=1 if p["side"]=="LONG" else -1
            risk=(entry-stop)*direction
            if risk<=0:
                p["status"]="INVALID_ENTRY_RISK";continue
            p["entry"]=str(entry)
            p["tp1"]=str(entry+direction*0.75*risk)
            p["tp3"]=str(entry+direction*2.25*risk)
            p["status"]="OPEN"
        last=p["last_checked_utc"]
        if last and datetime.fromisoformat(last)+timedelta(minutes=15)<datetime.fromisoformat(oldest):
            p["status"]="DATA_GAP";p["events"]=(p["events"]+"|DATA_GAP").strip("|")
            continue
        direction=1 if p["side"]=="LONG" else -1
        entry=float(p["entry"]);stop=float(p["stop"])
        risk=(entry-stop)*direction
        stage=int(p["stage"]);left=float(p["remaining"]);gross=float(p["gross_R"])
        for timestamp in ts:
            if timestamp<start or (last and timestamp<=last):continue
            # No missing 15min candles inside the processed span.
            if last and datetime.fromisoformat(timestamp)-datetime.fromisoformat(last)>timedelta(minutes=15):
                p["status"]="DATA_GAP";p["events"]=(p["events"]+"|DATA_GAP").strip("|")
                break
            b=bars[timestamp]
            protection=stop if stage==0 else entry
            touched=(b.l<=protection if direction==1 else b.h>=protection)
            gap=(b.o<=protection if direction==1 else b.o>=protection)
            p["last_checked_utc"]=timestamp
            if touched:
                px=b.o if gap else protection
                gross+=left*(px-entry)*direction/risk
                p["status"]="CLOSED"
                p["exit_time_utc"]=timestamp
                p["events"]=(p["events"]+"|"+("GAP_STOP" if gap else "STOP")).strip("|")
                left=0
                break
            hit1=(b.h>=float(p["tp1"]) if direction==1 else b.l<=float(p["tp1"]))
            hit3=(b.h>=float(p["tp3"]) if direction==1 else b.l<=float(p["tp3"]))
            if stage==0 and hit1:
                gross+=0.2*0.75
                left=0.8;stage=1
                p["events"]=(p["events"]+"|TP1_20PCT").strip("|")
            if hit3:
                gross+=left*2.25
                left=0
                p["events"]=(p["events"]+"|TP3_REST").strip("|")
                p["status"]="CLOSED";p["exit_time_utc"]=timestamp
                break
            last=timestamp
        p["stage"]=str(stage)
        p["remaining"]=str(round(left,10))
        p["gross_R"]=str(round(gross,8))
        if p["status"]=="CLOSED":p["net_R"]=str(round(gross-COST_PER_OZ/risk,6))
    return positions

def main():
    previous={r["id"]:r for r in read_csv(DEST)}
    snapshots=read_csv(SNAP)
    add_signals(previous,snapshots)
    path=ROOT/"gold_signal_bot_v3_9_5_diagnose (2).py"
    spec=importlib.util.spec_from_file_location("gold_shadow_data",path)
    bot=importlib.util.module_from_spec(spec);sys.modules[spec.name]=bot;spec.loader.exec_module(bot)
    candles=bot.candles("15min",320)
    update(previous,candles,datetime.now(timezone.utc))
    write_csv(DEST,[previous[k] for k in sorted(previous)])
    print("B/C 20/80 forward shadow:",len(previous),"trades,",
          sum(p["status"]=="CLOSED" for p in previous.values()),"closed,",
          sum(p["status"]=="OPEN" for p in previous.values()),"open; no broker orders")
if __name__=="__main__":main()
