#!/usr/bin/env python3
"""Classify XAU/USD historical candles by CME GC reference trading session.
IMPORTANT: CME futures hours are a PROXY, not a verified schedule for spot XAU/USD.
Outputs tagged original bars plus session counts. Never silently delete prices.
"""
import csv,json
from collections import Counter
from datetime import datetime,time,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent/"gold_data_audit"
CT=ZoneInfo("America/Chicago")

def reference_session(utc):
    local=utc.astimezone(CT)
    wd=local.weekday()  # Monday=0 ... Sunday=6
    minute=local.hour*60+local.minute
    # CME standard GC Globex reference: Sunday 17:00 CT to Friday 16:00 CT,
    # daily maintenance around 16:00-17:00 CT. Check holidays separately.
    if wd==5 or (wd==4 and minute>=16*60) or (wd==6 and minute<17*60):
        return "WEEKEND_REF_CLOSED"
    if 0<=wd<=3 and 16*60<=minute<17*60:
        return "DAILY_BREAK_REF"
    return "REF_OPEN_NOT_VERIFIED_SPOT"

summary={"reference":"CME GC futures session as comparison ONLY; does not establish spot broker tradeability",
         "assumptions":["America/Chicago DST-aware","Sun 17:00 CT to Fri 16:00 CT, daily 16:00-17:00 maintenance","Holiday and exceptional session changes not included","Label indicates candle OPEN time; boundary-crossing candles may overlap closed intervals"],
         "intervals":[]}
for interval,minutes in [("15min",15),("1h",60)]:
    file=ROOT/f"gold_{interval}_2026_aug_oct.csv"
    with file.open(newline="",encoding="utf-8") as f:original=list(csv.DictReader(f))
    counts=Counter();weekend_days=Counter();samples=[];rows=[]
    for r in original:
        t=datetime.fromisoformat(r["utc"])
        label=reference_session(t)
        counts[label]+=1
        if label=="WEEKEND_REF_CLOSED":
            weekend_days[t.date().isoformat()]+=1
            if len(samples)<12:samples.append({"utc":t.isoformat(),"close":r["close"]})
        rows.append({**r,"cme_reference_session":label})
    with (ROOT/f"gold_{interval}_session_tagged.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
    summary["intervals"].append({"interval":interval,"bars":len(rows),"session_counts":dict(counts),
       "closed_reference_pct":round(100*(counts["WEEKEND_REF_CLOSED"]+counts["DAILY_BREAK_REF"])/max(len(rows),1),2),
       "weekend_utc_days_count":len(weekend_days),"closed_samples":samples})
    print(interval,"bars",len(rows),"reference categories",dict(counts))
summary["next_action"]="Inspect weekends and holidays with instrument's actual venue; compare backtests all bars vs reference-eligible bars, without refitting on test months."
(ROOT/"gold_reference_sessions_report.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("Research-only; no Telegram or order calls, no source bars removed.")
