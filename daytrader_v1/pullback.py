"""Fibonacci observation zones from confirmed M15 swings; no order execution."""
from .structure import analyze

RATIOS = (.236, .382, .5, .618, .786)

def zone(candles, side, span=2):
    s = analyze(candles, span)
    if side not in ("BUY", "SELL") or s["direction"] != side:
        return None
    starts = s["swing_lows"] if side == "BUY" else s["swing_highs"]
    ends = s["swing_highs"] if side == "BUY" else s["swing_lows"]
    end = ends[-1]
    candidates = [p for p in starts if p["time"] < end["time"]]
    if not candidates:
        return None
    start = candidates[-1]
    a, b = start["price"], end["price"]
    if (side == "BUY" and b <= a) or (side == "SELL" and b >= a):
        return None
    levels = {str(r): b + (a-b)*r for r in RATIOS}
    return dict(side=side, start=a, end=b, start_time=start["time"],
                end_time=end["time"], confirmed_at=max(start["confirmed_at"], end["confirmed_at"]),
                levels=levels, lower=min(levels["0.5"], levels["0.618"]),
                upper=max(levels["0.5"], levels["0.618"]))

def observe(z, candles, span=2):
    """Evaluate a stored zone against closed M5 candles after its confirmation.
    Timestamp convention must be candle CLOSE time in UTC across both frames.
    """
    if not z:
        return dict(status="NO_ZONE")
    analyze(candles, span)
    rows = [c for c in candles if c["timestamp"] > z["confirmed_at"]]
    if not rows:
        return dict(status="WAIT")
    buy = z["side"] == "BUY"
    if any(float(c["low"]) <= z["start"] if buy else float(c["high"]) >= z["start"] for c in rows):
        return dict(status="INVALIDATED", reason="impulse origin breached")
    if any(float(c["high"]) > z["end"] if buy else float(c["low"]) < z["end"] for c in rows):
        return dict(status="INVALIDATED", reason="new impulse extreme; reassess zone")
    touched = [i for i,c in enumerate(rows) if float(c["low"]) <= z["upper"] and float(c["high"]) >= z["lower"]]
    if not touched:
        return dict(status="WAIT")
    # Only a fresh closed candle following a recent touch can be a candidate.
    if len(rows)-1-touched[-1] > 3:
        return dict(status="EXPIRED")
    if len(rows) < 2:
        return dict(status="TOUCHED")
    c, prev = rows[-1], rows[-2]
    p, o = float(c["close"]), float(c["open"])
    confirmed = (p > o and p > float(prev["high"]) and p > z["upper"]) if buy else (p < o and p < float(prev["low"]) and p < z["lower"])
    return dict(status="CANDIDATE" if confirmed else "TOUCHED",
                timestamp=c["timestamp"], close=p)
