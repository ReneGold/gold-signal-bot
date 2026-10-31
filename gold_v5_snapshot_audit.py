#!/usr/bin/env python3
"""Audit new Gold V5 contemporaneous signal snapshots without rewriting history."""
import csv, json, math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
with (ROOT/"gold_v5_forward_ledger.csv").open(newline="",encoding="utf-8") as f:
    ledger=list(csv.DictReader(f))
path=ROOT/"gold_v5_signal_snapshots.json"
snapshots=json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
if not isinstance(snapshots,list): raise ValueError("Signal snapshots must be a JSON list")
forward=[r for r in ledger if r.get("cohort")=="FORWARD"]
by_signal={r["signal_utc"]:r for r in forward}
errors=[];warnings=[];seen=set();valid=0
required_numeric=("ema20_15m","ema50_15m","ema20_previous_15m","atr14_15m",
                  "ema20_1h","ema50_1h","atr14_1h","ema_gap_1h_over_atr",
                  "signal_ema20_distance_atr","risk_distance")
for snap in snapshots:
    if not isinstance(snap,dict):
        errors.append("Non-object snapshot");continue
    key=snap.get("signal_utc")
    if key in seen: errors.append("Duplicate snapshot: "+str(key))
    seen.add(key)
    match=by_signal.get(key)
    if not match:
        errors.append("Snapshot does not match observed FORWARD signal: "+str(key));continue
    if snap.get("side")!=match.get("side"):
        errors.append("Direction mismatch: "+str(key))
    if snap.get("captured_at_decision") is not True:
        errors.append("Snapshot missing original decision flag: "+str(key))
    for name in required_numeric:
        value=snap.get(name)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            errors.append("Invalid "+name+" for "+str(key))
    if any(snap.get(x) is not None for x in ("broker_bid_ask","spread","slippage","support_resistance_zone")):
        warnings.append("Unverified execution/zone fields are populated: "+str(key))
    try:
        if datetime.fromisoformat(snap["decision_utc"]) <= datetime.fromisoformat(key):
            errors.append("Invalid decision ordering: "+str(key))
    except (KeyError,TypeError,ValueError):
        errors.append("Invalid timestamps: "+str(key))
    valid+=1
unmatched=[r["signal_utc"] for r in forward if r["signal_utc"] not in seen]
# Signals recorded before this feature's deployment cannot be retroactively validated.
if unmatched:
    warnings.append(str(len(unmatched))+" pre-existing or undocumented FORWARD signals; do not infer indicator history.")
status="FAIL" if errors else ("WAITING_FOR_NEW_SIGNALS" if not snapshots else "PASS")
report={"generated_utc":datetime.now(timezone.utc).isoformat(),"status":status,
        "forward_signals":len(forward),"snapshots":len(snapshots),
        "validated_snapshots":valid,"unmatched_forward_signals":unmatched,
        "errors":errors,"warnings":warnings,
        "note":"No backfilling. A green check with zero snapshots verifies wiring only, not signal data completeness."}
(ROOT/"gold_v5_snapshot_audit.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
if errors: raise SystemExit(1)
