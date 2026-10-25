"""Research-only gold news and volatility gate. No orders, no live calendar feed.

High-impact calendar events MUST be provided explicitly with UTC timestamps,
preferably from a verified economic-calendar source. Empty events are marked
UNKNOWN, not proof of a news-free session.
ATR and latest true range must use only fully closed bars.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta
from math import isfinite

@dataclass(frozen=True)
class Event:
    time_utc:datetime
    name:str
    impact:str="HIGH"
    currency:str="USD"

@dataclass(frozen=True)
class GatePolicy:
    news_before_minutes:int=30
    news_after_minutes:int=30
    max_range_atr:float=2.5
    min_atr_pct:float=0.025
    max_atr_pct:float=0.35

def check(*,assessed_at_utc,events,latest_close,latest_true_range,
          atr_15m,policy=GatePolicy()):
    if assessed_at_utc.tzinfo is None:raise ValueError("UTC-aware assessment time required")
    if any(not isinstance(x,(int,float)) or not isfinite(x) for x in
           (latest_close,latest_true_range,atr_15m)):raise ValueError("Invalid volatility inputs")
    if latest_close<=0 or atr_15m<=0 or latest_true_range<0:
        raise ValueError("Non-positive price or ATR")
    if (policy.news_before_minutes<0 or policy.news_after_minutes<0 or
        policy.max_range_atr<=0 or policy.min_atr_pct<=0 or
        policy.max_atr_pct<=policy.min_atr_pct):
        raise ValueError("Invalid thresholds")
    reasons=[]
    near=[]
    for e in events:
        if e.time_utc.tzinfo is None:raise ValueError("News timestamps require timezone")
        if e.impact.upper()!="HIGH" or e.currency.upper()!="USD":continue
        minutes=(e.time_utc-assessed_at_utc).total_seconds()/60
        if -policy.news_after_minutes<=minutes<=policy.news_before_minutes:
            near.append(e.name)
    if near:reasons.append("HIGH_IMPACT_USD_NEWS_WINDOW")
    range_atr=latest_true_range/atr_15m
    atr_pct=100*atr_15m/latest_close
    if range_atr>policy.max_range_atr:reasons.append("EXCESSIVE_15M_RANGE")
    if atr_pct<policy.min_atr_pct:reasons.append("LOW_ATR_REGIME")
    if atr_pct>policy.max_atr_pct:reasons.append("HIGH_ATR_REGIME")
    return {"approved":not reasons,"reasons":reasons,
            "calendar_status":"EVENT_LIST_SUPPLIED" if events else "UNKNOWN_NO_EVENTS_SUPPLIED",
            "nearby_high_impact_usd_events":near,
            "true_range_over_atr":round(range_atr,4),"atr_pct":round(atr_pct,4)}
