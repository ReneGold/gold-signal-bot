"""SMC price-pattern proxies, not evidence of institutional orders.
All timestamps are UTC candle close times. No execution or signal approval.
"""
from .structure import analyze

def analyze_smc(candles, span=2):
    if type(span) is not int or span < 1:
        raise ValueError("invalid span")
    if len(candles) < 2*span+4:
        return {"status": "INSUFFICIENT_DATA", "events": [], "gaps": [], "orderblocks": []}
    # Full input validation; previous structure excludes the event candle.
    current = analyze(candles, span)
    prior = analyze(candles[:-1], span)
    c, prev = candles[-1], candles[-2]
    o,h,l,p = (float(c[k]) for k in ("open","high","low","close"))
    prev_close = float(prev["close"])
    resistance, support = prior.get("resistance"), prior.get("support")
    events = []
    for side, level, crossed, swept in (
        ("BUY", resistance,
         resistance is not None and prev_close <= resistance < p,
         resistance is not None and h > resistance and p < resistance),
        ("SELL", support,
         support is not None and prev_close >= support > p,
         support is not None and l < support and p > support)):
        if crossed:
            direction = prior["direction"]
            kind = "BOS" if direction == side else "CHOCH" if direction in ("BUY","SELL") else "BREAK"
            events.append(dict(kind=kind, side=side, level=level, timestamp=c["timestamp"]))
        if swept:
            events.append(dict(kind="LIQUIDITY_SWEEP",
                               side="SELL" if side=="BUY" else "BUY",
                               level=level,timestamp=c["timestamp"]))
    # Three-candle imbalance; only the part not subsequently filled is retained.
    gaps = []
    for i in range(2,len(candles)):
        a,b = candles[i-2],candles[i]
        ah,al,bh,bl = float(a["high"]),float(a["low"]),float(b["high"]),float(b["low"])
        later = candles[i+1:]
        if bl > ah:
            upper = min([bl]+[float(x["low"]) for x in later])
            if upper > ah:
                gaps.append(dict(side="BUY",lower=ah,upper=upper,created_at=b["timestamp"]))
        if bh < al:
            lower = max([bh]+[float(x["high"]) for x in later])
            if lower < al:
                gaps.append(dict(side="SELL",lower=lower,upper=al,created_at=b["timestamp"]))
    # Orderblock proxy: last opposite-colored candle before a confirmed BOS.
    blocks = []
    for event in events:
        if event["kind"] != "BOS":
            continue
        buy = event["side"] == "BUY"
        for x in reversed(candles[-11:-1]):
            xo,xc = float(x["open"]),float(x["close"])
            if (xc < xo if buy else xc > xo):
                lower,upper = float(x["low"]),float(x["high"])
                # Exclude zones already breached after their origin.
                after = [y for y in candles if y["timestamp"] > x["timestamp"]]
                if not any(float(y["close"]) < lower if buy else float(y["close"]) > upper for y in after):
                    blocks.append(dict(side=event["side"],lower=lower,upper=upper,
                                       origin=x["timestamp"],confirmed_at=c["timestamp"]))
                break
    return dict(status="OK",as_of=c["timestamp"],direction=current["direction"],
                support=support,resistance=resistance,events=events,gaps=gaps,
                orderblocks=blocks)
