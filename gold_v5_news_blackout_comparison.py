#!/usr/bin/env python3
"""Counterfactual news blackout comparison for observed FORWARD paper signals only.
No historical entry reconstruction, no live trades and no modification to ledger.
"""
import csv,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
with (P/"gold_v5_forward_ledger.csv").open(newline="",encoding="utf-8") as f:
 rows=[r for r in csv.DictReader(f) if r.get("cohort")=="FORWARD"]
calendar=json.loads((P/"gold_v5_calendar_verification.json").read_text(encoding="utf-8"))
source=json.loads((P/"gold_v5_us_news_calendar.json").read_text(encoding="utf-8"))
approved={(e["category"],e["release_utc"]) for e in calendar.get("events",[])
          if e.get("verification")=="MATCHES_SNAPSHOT"}
events=[e for e in source.get("future_events",[])
        if (e.get("category"),e.get("release_utc")) in approved]
windows=[15,30,60]
results={}
for window in windows:
 flagged=[];outside=[]
 for row in rows:
  decision=datetime.fromisoformat(row["entry_utc"])
  nearest=next((event for event in events
      if abs((decision-datetime.fromisoformat(event["release_utc"])).total_seconds())<=window*60),None)
  if nearest:
   flagged.append({"signal_utc":row["signal_utc"],"status":row["status"],
                   "category":nearest["category"],"release_utc":nearest["release_utc"],
                   "net_R_if_closed":float(row["net_R"]) if row["status"]=="CLOSED_PAPER" else None})
  else:outside.append(row)
 results[str(window)]={"flagged_signals":len(flagged),"flagged":flagged,
   "unflagged_closed_net_R":round(sum(float(r["net_R"]) for r in outside if r["status"]=="CLOSED_PAPER"),5),
   "unflagged_closed_count":sum(r["status"]=="CLOSED_PAPER" for r in outside)}
status=("CALENDAR_INCOMPLETE" if calendar.get("third_party_status") not in ("THIRD_PARTY_UNVERIFIED","OK_BLS_ONLY")
   or not calendar.get("reference_valid") or calendar.get("missing_categories") else "LIMITED_VERIFIED_SNAPSHOT")
report={"generated_utc":datetime.now(timezone.utc).isoformat(),
 "status":status,"scope":"FORWARD paper signals only","observed_forward_signal_count":len(rows),
 "verified_reference_event_count":len(events),"blackout_comparisons_minutes_each_side":results,
 "filter_active":False,"strategy_or_ledger_modified":False,
 "limitation":"Not a historical calendar backtest. Only the CURRENT limited upcoming calendar is available; past event coverage is missing. Zero flagged signals cannot establish news-filter value. Missing FOMC and revisions possible. No replacement trades are simulated."}
(P/"gold_v5_news_blackout_comparison.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
