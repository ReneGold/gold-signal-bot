#!/usr/bin/env python3
"""Gold V5 independent conservative paper risk-overlay; no orders or strategy edits.
Illustrative EUR equity / USD per oz. Broker contract and FX not verified.
Never label position sizing as executable until contract_value validated.
"""
import csv,json,math,os
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
LEDGER=ROOT/"gold_v5_forward_ledger.csv"
REPORT=ROOT/"gold_v5_risk_report.json"
EQUITY_EUR=5000.0
RISK_FRACTION=0.0025   # 0.25% per position
DAILY_LIMIT_R=2.0      # 0.5% equity at consistent risk size
MAX_CONSECUTIVE_LOSSES=3
MAX_EQUITY_DD_R=6.0
MAX_ACTIVE=1
BERLIN=ZoneInfo("Europe/Berlin")
with LEDGER.open(newline="",encoding="utf-8") as f:
    all_rows=list(csv.DictReader(f))
forward=[r for r in all_rows if r.get("cohort")=="FORWARD"]
closed=sorted((r for r in forward if r.get("status")=="CLOSED_PAPER"),key=lambda x:x["exit_utc"])
active=[r for r in forward if r.get("status") in ("OPEN_PAPER","PENDING_ENTRY")]
today=datetime.now(timezone.utc).astimezone(BERLIN).date()
daily=[r for r in closed if datetime.fromisoformat(r["exit_utc"]).astimezone(BERLIN).date()==today]
today_R=sum(float(r["net_R"]) for r in daily)
loss_streak=0
for r in reversed(closed):
    if float(r["net_R"])<0:loss_streak+=1
    else:break
eq=peak=drawdown=0.0
for r in closed:
    eq+=float(r["net_R"])
    peak=max(peak,eq)
    drawdown=max(drawdown,peak-eq)
reasons=[]
if today_R<=-DAILY_LIMIT_R:reasons.append("Daily closed-paper loss threshold reached")
if loss_streak>=MAX_CONSECUTIVE_LOSSES:reasons.append("Consecutive losing trades threshold reached")
if drawdown>=MAX_EQUITY_DD_R:reasons.append("Closed-equity drawdown threshold reached")
if len(active)>MAX_ACTIVE:reasons.append("More than one simultaneous paper position")
if any(r.get("status")=="UNRESOLVED_DATA_GAP" for r in forward):
    reasons.append("Unresolved missing execution data")
report={
 "generated_utc":datetime.now(timezone.utc).isoformat(),
 "mode":"READ_ONLY_PAPER_RISK_OVERLAY",
 "example_account_eur":EQUITY_EUR,
 "illustrative_risk_fraction":RISK_FRACTION,
 "illustrative_max_loss_per_trade_eur":round(EQUITY_EUR*RISK_FRACTION,2),
 "limits":{"daily_closed_loss_R":DAILY_LIMIT_R,"max_consecutive_losses":MAX_CONSECUTIVE_LOSSES,
           "max_closed_drawdown_R":MAX_EQUITY_DD_R,"max_open_positions":MAX_ACTIVE},
 "observed":{"closed_trades":len(closed),"open_and_pending":len(active),
             "today_closed_net_R":round(today_R,5),"loss_streak":loss_streak,
             "closed_drawdown_R":round(drawdown,5)},
 "paper_gate":"BLOCK_NEW_ENTRIES" if reasons else "NO_LIMIT_BREACH",
 "breach_reasons":reasons,
 "position_size_lots":None,
 "important":["Risk thresholds are research examples, NOT approved real trading limits.",
              "Position size must be withheld until PU Prime contract size, lot step, FX rate, margin and actual spread are verified.",
              "Daily realized and closed-trade drawdown do not account for intratrade unrealized losses.",
              "This read-only overlay does not actually stop the observer from recording new signals or block broker orders.",
              "No broker integration, orders or Telegram messages are sent."]
}
REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
