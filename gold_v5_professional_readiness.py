#!/usr/bin/env python3
"""Gold V5 four professional research readiness gates (read-only).
No live orders, no changes to frozen signal decisions or forward ledger.
Unknown external inputs are explicitly NOT VERIFIED, never silently treated as safe.
"""
import csv, json, math
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def evaluate(ledger, snapshots, news_events=None, broker_quotes=None):
    forward=[r for r in ledger if r.get("cohort")=="FORWARD"]
    closed=[r for r in forward if r.get("status")=="CLOSED_PAPER"]
    by_signal={r.get("signal_utc"):r for r in forward}
    n=len(closed)
    news={
      "status":"NOT_VERIFIED" if news_events is None else "RESEARCH_ONLY",
      "source":"NONE" if news_events is None else "USER_SUPPLIED_UNVERIFIED",
      "high_impact_usd_events":None if news_events is None else len(news_events),
      "release_time_timezone_verified":False,
      "proposed_blackout_before_minutes":30,
      "proposed_blackout_after_minutes":30,
      "enforced_for_existing_signals":False,
      "note":"No licensed/reliable verified economic-calendar feed is connected. Proposed window is NOT applied to paper entries."}
    quote_ok=bool(broker_quotes) and all(k in broker_quotes for k in ("timestamp_utc","bid","ask","symbol"))
    spread=None
    if quote_ok:
        bid=float(broker_quotes["bid"]);ask=float(broker_quotes["ask"])
        if math.isfinite(bid) and math.isfinite(ask) and 0<bid<=ask:
            spread=round(ask-bid,5)
        else:quote_ok=False
    spread_vol={
      "status":"RESEARCH_ONLY" if quote_ok else "NOT_VERIFIED",
      "verified_live_bid_ask":False,
      "broker_quote_available":quote_ok,
      "illustrative_quote_spread_usd":spread,
      "actual_spread_limit":None,
      "execution_filter_active":False,
      "recent_signal_atr14_15m":snapshots[-1].get("atr14_15m") if snapshots else None,
      "volatility_guard_active":False,
      "note":"ATR diagnostics exist for future snapshots; no validated broker spread, session or empirical volatility thresholds."}
    unresolved=sum(r.get("status")=="UNRESOLVED_DATA_GAP" for r in forward)
    positions=sum(r.get("status") in ("OPEN_PAPER","PENDING_ENTRY") for r in forward)
    exit_counts={label:sum(r.get("exit_reason")==label for r in closed) for label in ("TP","STOP","TIME")}
    entry_exit={
      "status":"PAPER_RULES_PRESENT_NOT_EXECUTION_VALIDATED",
      "pending_entry_count":sum(r.get("status")=="PENDING_ENTRY" for r in forward),
      "open_paper_count":sum(r.get("status")=="OPEN_PAPER" for r in forward),
      "unresolved_data_gap_count":unresolved,
      "closed_exit_reasons":exit_counts,
      "planned_reward_to_risk":2.0,
      "max_observation_bars":16,
      "stop_first_if_both_hit":True,
      "broker_order_manager_active":False,
      "intrabar_fill_order_verified":False,
      "note":"Paper logic uses completed OHLC candles and an assumed fixed 0.8 USD cost; no broker stop, latency, partial fills, or realistic gap simulation."}
    values=[float(r["net_R"]) for r in closed]
    if not all(math.isfinite(v) for v in values): raise ValueError("Nonfinite trade R")
    # Existing net_R already subtracts 0.8 price units per trade. Vary *additional*
    # adverse price movement, in price dollars, relative to that assumption.
    extra_costs=(0.0,0.5,1.0,2.0)
    sensitivity={}
    for extra in extra_costs:
        adjusted=[]
        for r in closed:
            risk=float(r["risk"])
            if risk<=0:raise ValueError("Nonpositive risk")
            adjusted.append(float(r["net_R"])-extra/risk)
        sensitivity[str(extra)]=round(sum(adjusted),5)
    validation={
      "status":"INSUFFICIENT_FORWARD_SAMPLE" if n<30 else "EXPLORATORY_ONLY",
      "forward_closed_count":n,
      "backfill_excluded":True,
      "forward_net_R_at_existing_assumed_cost":round(sum(values),5),
      "extra_adverse_price_cost_usd_per_trade_to_total_net_R":sensitivity,
      "independent_out_of_sample_validated":False,
      "verified_broker_execution":False,
      "ready_for_live_trading":False,
      "note":"Sensitivity is not a broker execution backtest. No confidence in profitability from sparse forward observations."}
    return {"generated_utc":datetime.now(timezone.utc).isoformat(),
      "mode":"RESEARCH_ONLY_NO_TRADE_GATE_CHANGES",
      "modules":{"news_blackout":news,"spread_volatility":spread_vol,
                 "entry_exit":entry_exit,"realistic_validation":validation},
      "forward_ledger_count":len(forward),
      "matched_signal_snapshots":sum(s.get("signal_utc") in by_signal for s in snapshots),
      "critical":"No live order capability. News and spread data missing; do not claim filters are operational."}

def main():
    with (ROOT/"gold_v5_forward_ledger.csv").open(newline="",encoding="utf-8") as f:
        ledger=list(csv.DictReader(f))
    snapshots=json.loads((ROOT/"gold_v5_signal_snapshots.json").read_text(encoding="utf-8"))
    result=evaluate(ledger,snapshots)
    (ROOT/"gold_v5_professional_readiness.json").write_text(
      json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
