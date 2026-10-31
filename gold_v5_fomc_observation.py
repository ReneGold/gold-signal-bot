#!/usr/bin/env python3
"""Independent scheduled-FOMC observer and historical paper signal comparison.
Official fixed reference only; no modifications to original strategy or trades.
"""
import csv,json
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
reference=json.loads((ROOT/"gold_v5_fomc_reference.json").read_text(encoding="utf-8"))
with (ROOT/"gold_v5_forward_ledger.csv").open(newline="",encoding="utf-8") as f:
    forward=[r for r in csv.DictReader(f) if r.get("cohort")=="FORWARD"]
now=datetime.now(timezone.utc)
events=[]
for event in reference["events"]:
    instant=datetime.fromisoformat(event["release_utc"])
    minutes=(instant-now).total_seconds()/60
    matches=[]
    for r in forward:
        decision=datetime.fromisoformat(r["entry_utc"])
        difference=(decision-instant).total_seconds()/60
        if abs(difference)<=60:
            matches.append({"signal_utc":r["signal_utc"],"difference_minutes":round(difference,2),
                "paper_status":r["status"]})
    events.append({**event,"minutes_until":round(minutes,2),
        "inside_proposed_30_minute_window":abs(minutes)<=30,
        "forward_signal_matches_within_60_minutes":matches})
report={"checked_utc":now.isoformat(),"mode":"OBSERVATION_ONLY",
 "official_reference_source":reference["source_urls"],
 "calendar_type":"FIXED_VERIFIED_REFERENCE_NOT_LIVE_FEED",
 "events":events,"future_covered_event_count":sum(e["minutes_until"]>=0 for e in events),
 "trading_filter_active":False,
 "limitations":["FOMC includes both statement and press conference; overlapping windows must be combined if activated in later research.",
 "December 2026 only; dates can change, and an unobserved calendar change would not be detected automatically.",
 "A historical signal with no match does not establish a news-free session.",
 "No paper entries are blocked or modified."]}
(ROOT/"gold_v5_fomc_observation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
