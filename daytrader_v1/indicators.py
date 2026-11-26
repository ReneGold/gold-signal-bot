"""Deterministic indicator features for paper trading.
Input timestamps are UTC candle close times; session_start is supplied by the session adapter.
VWAP is a typical-price approximation weighted by the supplied volume, not exchange VWAP.
"""
from math import isfinite
from .structure import analyze

def ema(values, n):
    if len(values) < n:
        return None
    v = sum(values[:n])/n
    alpha = 2/(n+1)
    for x in values[n:]:
        v += alpha*(x-v)
    return v

def wilder(values, n=14):
    if len(values) < n:
        return None
    v = sum(values[:n])/n
    for x in values[n:]:
        v = (v*(n-1)+x)/n
    return v

def features(candles, session_start=None, volume_kind=None):
    if len(candles) < 201:
        return dict(status="INSUFFICIENT_DATA")
    analyze(candles)
    close = [float(c["close"]) for c in candles]
    high = [float(c["high"]) for c in candles]
    low = [float(c["low"]) for c in candles]
    delta = [b-a for a,b in zip(close,close[1:])]
    gain = wilder([max(x,0) for x in delta])
    loss = wilder([max(-x,0) for x in delta])
    rsi = 50.0 if gain == loss == 0 else 100.0 if loss == 0 else 100-100/(1+gain/loss)
    tr = [max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1])) for i in range(1,len(close))]
    atr = wilder(tr)
    previous_atr = wilder(tr[:-1])
    vwap = None
    if session_start is not None and volume_kind in ("tick","trade") and candles[0]["timestamp"] <= session_start < candles[-1]["timestamp"]:
        rows = [c for c in candles if c["timestamp"] > session_start]
        try:
            volumes = [float(c["volume"]) for c in rows]
            if all(isfinite(v) and v>=0 for v in volumes) and sum(volumes)>0:
                vwap = sum((float(c["high"])+float(c["low"])+float(c["close"]))/3*v for c,v in zip(rows,volumes))/sum(volumes)
        except (KeyError,ValueError,TypeError,OverflowError):
            pass
    o = float(candles[-1]["open"])
    p,h,l = close[-1],high[-1],low[-1]
    width = h-l
    body = abs(p-o)/width if width else 0
    location = (p-l)/width if width else .5
    # Candidate confirmation only; final approval belongs to decision.py.
    bullish = p>o and p>high[-2] and body>=.5 and location>=.75
    bearish = p<o and p<low[-2] and body>=.5 and location<=.25
    return dict(status="OK",as_of=candles[-1]["timestamp"],close=p,
                ema20=ema(close,20),ema50=ema(close,50),ema200=ema(close,200),
                rsi14=rsi,atr14=atr,previous_atr14=previous_atr,
                atr_ratio=tr[-1]/previous_atr if previous_atr>0 else None,
                vwap=vwap,volume_kind=volume_kind if vwap is not None else None,
                body_fraction=body,close_location=location,
                price_action="BUY" if bullish else "SELL" if bearish else "NEUTRAL",
                momentum="BUY" if rsi>50 and p>close[-2] else "SELL" if rsi<50 and p<close[-2] else "NEUTRAL")
