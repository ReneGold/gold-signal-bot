#!/usr/bin/env python3
"""Read-only explanations for the FROZEN Gold V5 paper entry rules.
No invented 0-100 score. No orders or Telegram messages.
"""
import json
from collections import Counter
from pathlib import Path

def decide(*, fresh, market_open, sideways, trend, touched, confirmed, active, risk_allowed, already_seen):
    checks = {
        "fresh_closed_candle": bool(fresh),
        "reference_session_open": bool(market_open),
        "weak_or_sideways_1h": bool(sideways),
        "ema20_ema50_trend": bool(trend),
        "ema20_pullback_touched": bool(touched),
        "closed_candle_breakout": bool(confirmed),
        "no_active_position": not bool(active),
        "risk_gate_allows": bool(risk_allowed),
        "not_previously_recorded": not bool(already_seen),
    }
    order = [
        ("fresh_closed_candle","STALE_OR_MISSED_RUN"),
        ("reference_session_open","REFERENCE_SESSION_CLOSED"),
        ("weak_or_sideways_1h","MARKET_PHASE_BLOCKED"),
        ("ema20_ema50_trend","NO_EMA_TREND"),
        ("ema20_pullback_touched","NO_PULLBACK_TOUCH"),
        ("closed_candle_breakout","NO_BREAKOUT_CONFIRMATION"),
        ("no_active_position","POSITION_ALREADY_ACTIVE"),
        ("risk_gate_allows","RISK_LIMIT"),
        ("not_previously_recorded","SIGNAL_ALREADY_RECORDED")
    ]
    blockers = [label for key,label in order if not checks[key]]
    return {"qualified": not blockers, "primary_reason": blockers[0] if blockers else "ELIGIBLE",
            "all_reasons": blockers, "checks": checks, "score": None,
            "score_note": "Frozen Gold V5 uses Boolean rules, NOT the V3.9 65-point score."}

def make_report(records):
    # Only counted fresh real observations, never reconstructed historical candles.
    valid=[r for r in records if r.get("fresh") is True]
    counts=Counter(r.get("primary_reason","UNKNOWN") for r in valid)
    return {
        "mode":"OBSERVED_ONLY_NO_LOOKAHEAD",
        "observed_closed_candles":len(valid),
        "reason_counts":dict(sorted(counts.items())),
        "latest":records[-1] if records else None,
        "last_96":dict(sorted(Counter(r.get("primary_reason","UNKNOWN") for r in valid[-96:]).items())),
        "limitations":[
            "No V3.9 score is calculated in the frozen V5 strategy.",
            "Only actually processed fresh completed bars appear; missed GitHub executions are not invented.",
            "These diagnostics do not establish profitability or executable broker fills."
        ]
    }

def save_observation(path, item):
    path=Path(path)
    data=json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    if not isinstance(data,list): raise ValueError("Decision log must be a JSON array")
    key=item["candle_utc"]
    if not any(x.get("candle_utc")==key for x in data):
        data.append(item)
        data=data[-1500:]
        path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return data
