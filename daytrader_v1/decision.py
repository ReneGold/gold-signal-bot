"""Paper-only decision gate. Inputs must come from verified analysis and risk adapters."""
from math import isfinite

WEIGHTS = dict(structure=20, trend=15, levels=15, liquidity=15,
               price_action=15, momentum=10, fibonacci=5, volatility=5)
REQUIRED = ("data_verified", "closed_candles", "news_clear", "spread_clear",
            "session_clear", "pullback_confirmed", "entry_confirmed",
            "not_chasing", "target_verified", "stop_verified", "risk_verified")

def decide(s):
    def reject(reason):
        return {"signal": "NO TRADE", "reason": reason, "mode": "PAPER"}
    try:
        for key in REQUIRED:
            if s.get(key) is not True:
                return reject(key)
        side = s["side"]
        if side not in ("BUY", "SELL"):
            return reject("direction")
        if any(s.get(k) != side for k in ("h4", "h1", "m15", "m5")):
            return reject("timeframe conflict")
        points = s["points"]
        if set(points) != set(WEIGHTS) or any(
            type(points[k]) not in (int, float) or not isfinite(points[k])
            or not 0 <= points[k] <= WEIGHTS[k] for k in WEIGHTS):
            return reject("invalid score")
        score = sum(points.values())
        if score < 80:
            return reject("score below 80")
        if s["open_positions"] != 0 or not 0 <= s["loss_streak"] < 3:
            return reject("position or loss limit")
        e, sl, tp, cost, equity, used = (
            float(s[k]) for k in ("entry", "stop", "target", "cost_per_ounce",
                                  "equity_usd", "daily_planned_risk_usd"))
        if not all(isfinite(x) for x in (e, sl, tp, cost, equity, used)):
            return reject("invalid numbers")
        if min(e, sl, tp, equity) <= 0 or min(cost, used) < 0:
            return reject("invalid risk inputs")
        if not (sl < e < tp if side == "BUY" else tp < e < sl):
            return reject("invalid price geometry")
        risk = abs(e-sl)+cost
        reward = abs(tp-e)-cost
        rr = reward/risk
        if rr < 2:
            return reject("net RR below 2")
        budget = min(equity*.005, equity*.015-used)
        if budget <= 0:
            return reject("daily risk limit")
        return dict(signal=side, mode="PAPER", entry=e, stop=sl, target=tp,
                    net_rr=rr, score=score, max_ounces=budget/risk,
                    planned_risk_usd=budget, setup="trend_pullback")
    except (KeyError, TypeError, ValueError, OverflowError):
        return reject("missing or invalid inputs")
