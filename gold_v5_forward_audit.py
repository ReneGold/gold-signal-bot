#!/usr/bin/env python3
"""Gold V5: independent, read-only forward-trade audit and stress tests.

Input: CSV with one row per *closed* trade. Required fields: cohort, status,
net_R. Optional: signal_time_utc, trade_id, regime, and indicator snapshot
fields (ema9, ema21, atr, rsi, score, spread, entry, stop, take_profit).
The script NEVER changes strategy rules or source trading records.
Run: python3 gold_v5_forward_audit.py --csv forward_closed_trades.csv
     python3 gold_v5_forward_audit.py --csv ... --output audit.json
"""
import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

SNAPSHOT = ("ema9", "ema21", "atr", "rsi", "score", "spread", "entry", "stop", "take_profit")
STRESS_COST_R = (0.0, 0.10, 0.25, 0.50)

def audit(rows):
    eligible, errors, duplicates = [], [], set()
    excluded = {"backfill_or_recovered": 0, "not_closed": 0}
    for line, r in enumerate(rows, start=2):
        cohort = str(r.get("cohort", "")).strip().upper()
        if cohort != "FORWARD":
            excluded["backfill_or_recovered"] += 1
            continue
        if str(r.get("status", "")).strip().upper() not in ("CLOSED", "CLOSE"):
            excluded["not_closed"] += 1
            continue
        try:
            val = float(r["net_R"])
            if not math.isfinite(val):
                raise ValueError("nonfinite net_R")
        except (KeyError, ValueError, TypeError):
            errors.append("line %d: missing/invalid net_R" % line)
            continue
        tid = str(r.get("trade_id", "")).strip()
        if tid:
            if tid in duplicates:
                errors.append("line %d: duplicate trade_id %s" % (line, tid))
                continue
            duplicates.add(tid)
        eligible.append(dict(r, _r=val, _line=line))
    eligible.sort(key=lambda r: (str(r.get("signal_time_utc", "")), r["_line"]))
    values = [r["_r"] for r in eligible]

    def metrics(v):
        n = len(v)
        if not n:
            return {"n": 0, "net_R": 0, "expectancy_R": None,
                    "win_rate_pct": None, "profit_factor": None,
                    "max_closed_drawdown_R": None, "max_consecutive_losses": None}
        equity, peak, drawdown, losses, worst = 0.0, 0.0, 0.0, 0, 0
        for x in v:
            equity += x
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
            losses = losses + 1 if x < 0 else 0
            worst = max(worst, losses)
        wins = sum(x for x in v if x > 0)
        lost = -sum(x for x in v if x < 0)
        return {"n": n, "net_R": round(sum(v), 5),
                "expectancy_R": round(statistics.mean(v), 5),
                "win_rate_pct": round(100 * sum(x > 0 for x in v) / n, 2),
                "profit_factor": round(wins / lost, 5) if lost else None,
                "max_closed_drawdown_R": round(drawdown, 5),
                "max_consecutive_losses": worst}

    by_regime = defaultdict(list)
    missing = {field: 0 for field in SNAPSHOT}
    for r in eligible:
        by_regime[str(r.get("regime", "")).strip() or "UNKNOWN"].append(r["_r"])
        for field in SNAPSHOT:
            if str(r.get(field, "")).strip() == "":
                missing[field] += 1
    out = {
        "scope": "CLOSED FORWARD trades only (no backfill/recovered records)",
        "sample_size": len(values),
        "excluded": excluded,
        "row_errors": errors,
        "base": metrics(values),
        "cost_stress": {
            str(cost): metrics([x - cost for x in values])
            for cost in STRESS_COST_R
        },
        "regime_breakdown": {name: metrics(v) for name, v in sorted(by_regime.items())},
        "snapshot_missing_counts": missing,
        "sample_warning": (
            "INSUFFICIENT: fewer than 30 closed independent forward trades"
            if len(values) < 30 else
            "Sample size alone does not demonstrate edge or statistical significance"
        ),
        "limitations": [
            "The CSV must contain genuine time-ordered FORWARD trades, not synthetic backfill.",
            "Costs in R are hypothetical; calibrate with actual executable broker spread/slippage.",
            "Drawdown and loss streak use closed trades only; intratrade risk is excluded.",
            "Regime comparisons require independently assigned historical regime labels.",
            "No Monte Carlo assumptions are used to conceal a small observed sample.",
            "Not financial advice or an approval to trade live."
        ]
    }
    return out

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    with args.csv.open(newline="", encoding="utf-8-sig") as f:
        data = audit(csv.DictReader(f))
    result = json.dumps(data, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
    if data["row_errors"]:
        raise SystemExit("Data validation errors: see row_errors in output")

if __name__ == "__main__":
    main()
