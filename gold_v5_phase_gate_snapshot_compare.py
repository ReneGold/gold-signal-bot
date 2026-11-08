#!/usr/bin/env python3
"""Read-only paired gate diagnostic on actually observed Gold V5 closed candles.
Does not backfill missed bars, infer strong-H1 direction, or simulate trade returns.
"""
import json
from collections import Counter
from pathlib import Path

SOURCE = Path(__file__).with_name("gold_v5_decisions_observed.json")

def compare(records):
    observed = [r for r in records if r.get("fresh") is True and isinstance(r.get("checks"), dict)]
    blockers = Counter(r.get("primary_reason", "UNKNOWN") for r in observed if not r.get("qualified"))
    market_phase = [r for r in observed if "MARKET_PHASE_BLOCKED" in r.get("all_reasons", [])]
    only_gate = []
    for r in market_phase:
        c = r["checks"]
        all_other_checks = all(c.get(k) is True for k in (
            "fresh_closed_candle", "reference_session_open", "ema20_ema50_trend",
            "ema20_pullback_touched", "closed_candle_breakout",
            "no_active_position", "risk_gate_allows", "not_previously_recorded"))
        if all_other_checks and c.get("weak_or_sideways_1h") is False:
            only_gate.append({"decision_utc": r.get("decision_utc"), "side": r.get("side")})
    return {
        "mode": "OBSERVED_CANDLES_ONLY_NO_TRADES",
        "observed_closed_candles": len(observed),
        "primary_rejection_reasons": dict(sorted(blockers.items())),
        "market_phase_blocked_any_reason": len(market_phase),
        "otherwise_fully_confirmed_h1_blocked_upper_bound": len(only_gate),
        "potential_candidates_if_h1_gate_removed": only_gate,
        "strong_h1_alignment_verifiable_from_snapshots": False,
        "returns_or_new_trade_signals_calculated": False,
        "interpretation": "Upper bound only. H1 trend-direction alignment, fills, costs, and profit cannot be inferred from these records."
    }

if __name__ == "__main__":
    print(json.dumps(compare(json.loads(SOURCE.read_text(encoding="utf-8"))), indent=2, ensure_ascii=False))
