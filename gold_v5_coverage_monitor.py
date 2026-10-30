#!/usr/bin/env python3
"""Gold V5 observation coverage report, purely diagnostic, no signal backfill.
Checks elapsed wall-clock time between successful workflow observer executions.
A delayed/missing run may miss signals; never report absence of signals as evidence.
"""
import json,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
PATH=P/"gold_v5_coverage_report.json"
now=datetime.now(timezone.utc)
previous=P/"gold_v5_forward_summary.json"
previous_run=None
if previous.exists():
 try:
  s=json.loads(previous.read_text(encoding="utf-8"))
  previous_run=datetime.fromisoformat(s["as_of_utc"])
  if previous_run.tzinfo is None:previous_run=None
 except (KeyError,ValueError,TypeError,json.JSONDecodeError):pass
gap_minutes=(now-previous_run).total_seconds()/60 if previous_run else None
# GitHub's cron often executes later than requested. This is a potential
# coverage gap, NOT proof that a valid signal occurred.
warnings=[]
if gap_minutes is None:warnings.append("NO_PREVIOUS_HEARTBEAT")
elif gap_minutes>25:warnings.append("OBSERVER_GAP_OVER_25_MINUTES")
# Exact cron four times hourly at minute 9,24,39,54.
slot=now.replace(second=0,microsecond=0)
mins=(slot.minute-9)%15
lateness=mins+(now.second/60)
if lateness>10:warnings.append("START_OFFSET_OVER_10_MINUTES_FROM_CRON_SLOT")
report={
 "observed_at_utc":now.isoformat(),
 "previous_observer_at_utc":previous_run.isoformat() if previous_run else None,
 "minutes_since_previous_observer":round(gap_minutes,2) if gap_minutes is not None else None,
 "nominal_schedule_minutes_utc":[9,24,39,54],
 "minutes_since_most_recent_nominal_slot":round(lateness,2),
 "status":"WARN" if warnings else "PASS",
 "warnings":warnings,
 "notes":[
  "This is a heartbeat/coverage warning only; no historical alert can be declared an actual realtime signal.",
  "Only successful runs that saved the summary are visible to this local report; to discover failed GitHub jobs independently, inspect Actions history or scheduled monitor.",
  "Weekend/session downtime may generate benign warnings.",
  "The forward signal observer intentionally does not reconstruct missed historical entries."
 ]}
PATH.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
