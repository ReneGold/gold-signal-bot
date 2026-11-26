"""Causal market structure from chronological, verified closed OHLC candles."""
from math import isfinite

def analyze(candles, span=2):
    if type(span) is not int or span < 1:
        raise ValueError("invalid swing span")
    if len(candles) < 2*span+3:
        return dict(direction="UNKNOWN", reason="insufficient candles")
    rows = []
    previous = None
    for c in candles:
        if c.get("closed") is not True:
            raise ValueError("unclosed candle")
        t = c["timestamp"]
        if previous is not None and t <= previous:
            raise ValueError("timestamps must increase")
        previous = t
        o,h,l,p = (float(c[k]) for k in ("open","high","low","close"))
        if not all(isfinite(x) and x > 0 for x in (o,h,l,p)) or not l <= min(o,p) <= max(o,p) <= h:
            raise ValueError("invalid OHLC")
        rows.append((t,o,h,l,p))
    highs, lows = [], []
    for i in range(span,len(rows)-span):
        t,o,h,l,p = rows[i]
        neighbors = rows[i-span:i]+rows[i+1:i+span+1]
        confirmed = rows[i+span][0]
        if all(h > x[2] for x in neighbors):
            highs.append(dict(time=t, price=h, confirmed_at=confirmed))
        if all(l < x[3] for x in neighbors):
            lows.append(dict(time=t, price=l, confirmed_at=confirmed))
    direction = "UNKNOWN"
    hh = hl = lh = ll = False
    if len(highs)>=2 and len(lows)>=2:
        hh = highs[-1]["price"] > highs[-2]["price"]
        lh = highs[-1]["price"] < highs[-2]["price"]
        hl = lows[-1]["price"] > lows[-2]["price"]
        ll = lows[-1]["price"] < lows[-2]["price"]
        direction = "BUY" if hh and hl else "SELL" if lh and ll else "NEUTRAL"
    # A close beyond the protected swing invalidates the directional classification.
    close = rows[-1][4]
    if direction == "BUY" and close < lows[-1]["price"]:
        direction = "NEUTRAL"
    if direction == "SELL" and close > highs[-1]["price"]:
        direction = "NEUTRAL"
    return dict(direction=direction, hh=hh, hl=hl, lh=lh, ll=ll,
                swing_highs=highs, swing_lows=lows,
                support=lows[-1]["price"] if lows else None,
                resistance=highs[-1]["price"] if highs else None,
                as_of=rows[-1][0])

def multi_timeframe(frames, span=2):
    result = {}
    for tf in ("h4","h1","m15","m5"):
        result[tf] = analyze(frames.get(tf, []), span)
    directions = [v["direction"] for v in result.values()]
    side = directions[0] if len(set(directions)) == 1 and directions[0] in ("BUY","SELL") else "NO TRADE"
    return dict(side=side, frames=result)
