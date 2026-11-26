"""Provisional binary subcriteria for the 100-point paper-trading score.
Missing evidence earns zero, never an assumed pass. Hard gates remain in decision.py.
"""
from math import isfinite
from .decision import WEIGHTS

def number(x):
    return type(x) in (int,float) and isfinite(x)

def score_setup(side, frames, features, smc, zone, observation):
    if side not in ("BUY","SELL"):
        raise ValueError("invalid direction")
    buy = side == "BUY"
    def direction(tf):
        return frames.get(tf,{}).get("direction") == side
    def ordered(a,b):
        return number(a) and number(b) and (a>b if buy else a<b)
    f = features.get("m5",{})
    h = features.get("h1",{})
    m = frames.get("m15",{})
    z = zone or {}
    obs = observation or {}
    p = f.get("close")
    atr = f.get("atr14")
    lo,hi = z.get("lower"),z.get("upper")
    level = m.get("support" if buy else "resistance")
    zone_valid = z.get("side")==side and number(lo) and number(hi) and lo<hi
    overlap = zone_valid and number(level) and number(atr) and atr>0 and lo-atr<=level<=hi+atr
    touched = zone_valid and obs.get("status") in ("TOUCHED","CANDIDATE")
    def aligned_event(kind):
        return any(e.get("kind")==kind and e.get("side")==side and e.get("timestamp")==f.get("as_of")
                   for e in smc.get("events",[]))
    def aligned_zone(items):
        return zone_valid and any(g.get("side")==side and number(g.get("lower")) and number(g.get("upper"))
                    and g["lower"]<=hi and g["upper"]>=lo for g in items)
    ratio=f.get("atr_ratio")
    tests = {
        "structure": [(10,direction("m15")),(10,direction("m5"))],
        "trend": [(5,direction("h4")),(5,direction("h1")),(5,ordered(h.get("ema50"),h.get("ema200")))],
        "levels": [(10,overlap),(5,touched)],
        "liquidity": [(5,aligned_event("BOS") or aligned_event("LIQUIDITY_SWEEP") or aligned_event("CHOCH")),
                      (5,aligned_zone(smc.get("gaps",[]))),(5,aligned_zone(smc.get("orderblocks",[])))],
        "price_action": [(10,f.get("price_action")==side),(5,obs.get("status")=="CANDIDATE" and touched)],
        "momentum": [(5,f.get("momentum")==side),(5,ordered(f.get("ema20"),f.get("ema50")))],
        "fibonacci": [(5,touched)],
        "volatility": [(5,number(atr) and atr>0 and number(ratio) and .5<=ratio<=2.5)]
    }
    points={k:sum(w for w,passed in rows if passed) for k,rows in tests.items()}
    assert all(sum(w for w,_ in tests[k])==WEIGHTS[k] for k in WEIGHTS)
    return dict(points=points,score=sum(points.values()),criteria=tests,
                vwap_available=number(f.get("vwap")),mode="PAPER")
