#!/usr/bin/env python3
"""Gold V5 forward integrity audit. Fail closed on corrupt ledger, not on low signal count.
Checks chronology, duplicates, outcomes and risk geometry. No trading operations.
"""
import csv,json,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path

P=Path(__file__).resolve().parent
with (P/"gold_v5_forward_ledger.csv").open(newline="",encoding="utf-8") as f:
 rows=list(csv.DictReader(f))
issues=[];warnings=[];ids=set();forward=[]
def parse(value,label):
 try:
  t=datetime.fromisoformat(value)
  if t.tzinfo is None:raise ValueError("timezone missing")
  return t
 except (TypeError,ValueError):
  issues.append(f"Invalid {label} timestamp: {value!r}")
  return None
for n,r in enumerate(rows,1):
 key=r.get("signal_utc","")
 if key in ids:issues.append(f"Duplicate signal candle: {key}")
 ids.add(key)
 signal=parse(key,f"row {n} signal");entry=parse(r.get("entry_utc",""),f"row {n} entry")
 if signal and entry and entry<=signal:issues.append(f"Non-forward entry timestamp row {n}")
 if r.get("cohort") not in ("FORWARD","INITIAL_BACKFILL","FORWARD_RECOVERED"):
  issues.append(f"Unknown cohort row {n}: {r.get('cohort')}")
 if r.get("cohort")=="FORWARD":forward.append(r)
 status=r.get("status")
 if status not in ("PENDING_ENTRY","OPEN_PAPER","CLOSED_PAPER","UNRESOLVED_DATA_GAP"):
  issues.append(f"Unknown status row {n}: {status}")
 if status in ("OPEN_PAPER","CLOSED_PAPER"):
  try:
   entry_price=float(r["entry"]);stop=float(r["stop"]);target=float(r["target"]);risk=float(r["risk"])
   if risk<=0:issues.append(f"Non-positive risk row {n}")
   if r["side"]=="LONG" and not(stop<entry_price<target):issues.append(f"Invalid LONG bracket row {n}")
   if r["side"]=="SHORT" and not(target<entry_price<stop):issues.append(f"Invalid SHORT bracket row {n}")
  except (ValueError,KeyError):
   issues.append(f"Missing numeric bracket row {n}")
 if status=="CLOSED_PAPER":
  exit_t=parse(r.get("exit_utc",""),f"row {n} exit")
  if entry and exit_t and exit_t<entry:issues.append(f"Exit before entry row {n}")
  try:float(r["net_R"])
  except (ValueError,TypeError):issues.append(f"Missing return row {n}")
 if status=="PENDING_ENTRY" and r.get("entry"):
  issues.append(f"Pending entry incorrectly priced row {n}")
# Paper positions must not overlap in their actual entry/exit windows.
active=[]
for r in forward:
 if r["status"] not in ("OPEN_PAPER","PENDING_ENTRY","CLOSED_PAPER"):continue
 start=parse(r["entry_utc"],"forward entry")
 end=parse(r["exit_utc"],"forward exit") if r["status"]=="CLOSED_PAPER" else None
 if start:active.append((start,end or datetime.max.replace(tzinfo=timezone.utc),r["signal_utc"]))
active.sort()
for a,b in zip(active,active[1:]):
 if b[0]<a[1]:issues.append(f"Overlapping forward positions: {a[2]} vs {b[2]}")
summary_path=P/"gold_v5_forward_summary.json"
if summary_path.exists():
 summary=json.loads(summary_path.read_text(encoding="utf-8"))
 if summary.get("forward_signals")!=len(forward):
  issues.append("Summary/ledger forward signal count mismatch")
# Warning-only: no false inference from silent weekends, missing schedule or no trades.
if not forward:warnings.append("No independent forward sample yet")
report={"generated_utc":datetime.now(timezone.utc).isoformat(),"rows":len(rows),
        "forward_rows":len(forward),"errors":issues,"warnings":warnings,
        "status":"FAIL" if issues else "PASS",
        "note":"Integrity checks are not market-data quality, strategy profitability, or execution validation"}
(P/"gold_v5_integrity_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
sys.exit(1 if issues else 0)
