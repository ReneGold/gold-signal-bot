#!/usr/bin/env python3
"""Read-only FORWARD signal review; never changes trading decisions or ledger."""
import csv,json
from datetime import datetime,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
def read(name):return json.loads((P/name).read_text(encoding="utf-8"))
with (P/"gold_v5_forward_ledger.csv").open(newline="",encoding="utf-8") as f:
    trades=[r for r in csv.DictReader(f) if r.get("cohort")=="FORWARD"]
snapshots={x["signal_utc"]:x for x in read("gold_v5_signal_snapshots.json")}
verification=read("gold_v5_calendar_verification.json")
fomc=read("gold_v5_fomc_reference.json")
macro=read("gold_v5_us_news_calendar.json")
accepted={(e["category"],e["release_utc"]) for e in verification.get("events",[]) if e.get("verification")=="MATCHES_SNAPSHOT"}
events=[{"category":e["category"],"release_utc":e["release_utc"],"source":"VERIFIED_FIXED_SNAPSHOT"} for e in macro.get("future_events",[]) if (e.get("category"),e.get("release_utc")) in accepted]
events.extend({"category":e["category"],"release_utc":e["release_utc"],"source":"FOMC_FIXED_DECEMBER_REFERENCE"} for e in fomc.get("events",[]))
items=[]
for r in trades:
    when=datetime.fromisoformat(r["entry_utc"])
    snap=snapshots.get(r["signal_utc"])
    nearby=[]
    for event in events:
        delta=round((when-datetime.fromisoformat(event["release_utc"])).total_seconds()/60,1)
        if abs(delta)<=60:nearby.append({**event,"minutes_from_release":delta})
    items.append({
      "signal_utc":r["signal_utc"],"direction":r["side"],"phase":r["phase"],
      "entry_utc":r["entry_utc"],"entry":r["entry"] or None,
      "stop":r["stop"] or None,"target":r["target"] or None,
      "risk":r["risk"],"status":r["status"],
      "exit_reason":r["exit_reason"] or None,
      "net_R":float(r["net_R"]) if r["status"]=="CLOSED_PAPER" else None,
      "indicators_captured_at_signal":bool(snap),
      "ema20_15m":snap.get("ema20_15m") if snap else None,
      "ema50_15m":snap.get("ema50_15m") if snap else None,
      "atr14_15m":snap.get("atr14_15m") if snap else None,
      "ema20_1h":snap.get("ema20_1h") if snap else None,
      "ema50_1h":snap.get("ema50_1h") if snap else None,
      "atr14_1h":snap.get("atr14_1h") if snap else None,
      "signal_candle":snap.get("candle") if snap else None,
      "snapshot_note":"MISSING_HISTORICAL_NOT_RECONSTRUCTED" if not snap else "CAPTURED",
      "reference_news_within_60_minutes":nearby,
      "calendar_coverage":"PARTIAL_ONLY_UNKNOWN_OTHER_EVENTS"
    })
report={"generated_utc":datetime.now(timezone.utc).isoformat(),
 "mode":"READ_ONLY_FORWARD_REVIEW",
 "forward_signal_count":len(items),
 "captured_snapshots":sum(x["indicators_captured_at_signal"] for x in items),
 "historical_missing_snapshots":sum(not x["indicators_captured_at_signal"] for x in items),
 "observations":items,
 "news_filter_active":False,
 "strategy_modified":False,
 "limitations":["Historical snapshots cannot be reconstructed without lookahead risk.",
 "Limited static news calendar is not an exhaustive historical verification.",
 "Paper entries and outcomes do not represent executable broker fills.",
 "One closed FORWARD trade is insufficient to infer profitability."]}
(P/"gold_v5_signal_review.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"status":"OK","reviewed_forward_signals":len(items),
                 "with_snapshot":report["captured_snapshots"]},ensure_ascii=False))
