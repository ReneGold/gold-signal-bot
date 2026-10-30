#!/usr/bin/env python3
"""Read-only Gold V5 paper performance report; original backfill excluded.
No signals, strategy parameters, orders, or Telegram changes.
"""
import csv,json
from datetime import datetime,timezone
from pathlib import Path

root=Path(__file__).resolve().parent
source=root/"gold_v5_forward_ledger.csv"
with source.open(newline="",encoding="utf-8") as f:
    all_rows=list(csv.DictReader(f))
rows=[r for r in all_rows if r.get("cohort")=="FORWARD"]
closed=sorted((r for r in rows if r["status"]=="CLOSED_PAPER"),key=lambda r:r["exit_utc"])
open_positions=[r for r in rows if r["status"] in ("OPEN_PAPER","PENDING_ENTRY")]
returns=[float(r["net_R"]) for r in closed]
wins=sum(v>0 for v in returns)
gains=sum(max(0,v) for v in returns)
losses=-sum(min(0,v) for v in returns)
equity=peak=drawdown=0.0
for v in returns:
    equity+=v
    peak=max(peak,equity)
    drawdown=max(drawdown,peak-equity)
report={
 "generated_utc":datetime.now(timezone.utc).isoformat(),
 "scope":"Only FORWARD cohort; excludes all INITIAL_BACKFILL and recovered records",
 "sample_size":len(closed),
 "forward_signals_total":len(rows),
 "forward_positions_open_or_pending":len(open_positions),
 "wins":wins,
 "losses_and_breakeven":len(closed)-wins,
 "win_rate_pct":round(100*wins/len(closed),2) if closed else None,
 "net_R":round(sum(returns),5),
 "average_R":round(sum(returns)/len(closed),5) if closed else None,
 "profit_factor":round(gains/losses,4) if losses else None,
 "max_closed_drawdown_R":round(drawdown,5),
 "first_signal_utc":min((r["signal_utc"] for r in rows),default=None),
 "last_signal_utc":max((r["signal_utc"] for r in rows),default=None),
 "limitations":[
  "A small or positive sample does not show profitability.",
  "Paper fills use indicative next-bar OHLC; no executable bid/ask, spread verification, holiday adjustments or slippage.",
  "CME reference trading session differs from spot XAUUSD broker session.",
  "GitHub scheduled executions may be delayed or missed; absence of trades does not prove absence of qualifying historical signals.",
  "Data feed and calendar validation remain open research items."
 ]
}
(root/"gold_v5_forward_performance.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("GOLD V5 PAPER FORWARD PERFORMANCE")
print(json.dumps(report,indent=2,ensure_ascii=False))
