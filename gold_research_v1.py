"""Gold Research V1 — isolated, deterministic 15-minute breakout candidate.

Research-only: no APIs, Telegram, broker, order placement, position sizing or P&L.
Hypothesis (UNPROVEN): confirmed 15m breakout of prior 20-bar high/low,
aligned with last fully closed 1h EMA20/50 trend. ATR14 for indicative stops.
Never assume that an XAUUSD candle implies an executable fill.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite

@dataclass(frozen=True)
class Bar:
    start: datetime  # UTC time at candle OPEN
    open: float
    high: float
    low: float
    close: float

def ema(values, period):
    a=2/(period+1)
    out=[values[0]]
    for x in values[1:]:out.append(a*x+(1-a)*out[-1])
    return out

def atr14(bars):
    true_ranges=[bars[0].high-bars[0].low]
    for cur,prev in zip(bars[1:],bars[:-1]):
        true_ranges.append(max(cur.high-cur.low,abs(cur.high-prev.close),abs(cur.low-prev.close)))
    a=sum(true_ranges[:14])/14
    for tr in true_ranges[14:]:a=(13*a+tr)/14
    return a

def _validate(bars, min_count, interval):
    if len(bars)<min_count:raise ValueError("insufficient warmup")
    for i,b in enumerate(bars):
        if b.start.tzinfo is None or b.start.utcoffset()!=timedelta(0):
            raise ValueError("UTC-aware candle opening timestamps required")
        px=(b.open,b.high,b.low,b.close)
        if not all(isfinite(v) and v>0 for v in px) or b.low>min(b.open,b.close) or b.high<max(b.open,b.close):
            raise ValueError("invalid OHLC")
        if i and b.start<=bars[i-1].start:raise ValueError("duplicate or reversed candles")
    if bars[-1].start-bars[-2].start!=interval:
        raise ValueError("latest two candles must be consecutive")

def candidate(b15,b1h,now):
    """Emit candidate only for newest *closed* 15m bar and completed H1 context."""
    if now.tzinfo is None or now.utcoffset()!=timedelta(0):
        raise ValueError("now must be timezone-aware UTC")
    _validate(b15,80,timedelta(minutes=15))
    _validate(b1h,80,timedelta(hours=1))
    close_time=b15[-1].start+timedelta(minutes=15)
    if close_time>now or now-close_time>timedelta(minutes=15):
        return {"status":"NO_SIGNAL","reason":"not_current_closed_15m"}
    h1_close=b1h[-1].start+timedelta(hours=1)
    if h1_close>close_time or close_time-h1_close>=timedelta(hours=1):
        return {"status":"NO_SIGNAL","reason":"h1_stale_or_incomplete"}
    hs=ema([b.close for b in b1h],20)
    hl=ema([b.close for b in b1h],50)
    if hs[-1]>hl[-1] and hs[-1]>hs[-2]:
        direction="LONG"
    elif hs[-1]<hl[-1] and hs[-1]<hs[-2]:
        direction="SHORT"
    else:
        return {"status":"NO_SIGNAL","reason":"no_confirmed_h1_trend"}
    prev=b15[-21:-1]  # exclude signal candle: NEVER look ahead
    signal=b15[-1]
    prior_high=max(b.high for b in prev)
    prior_low=min(b.low for b in prev)
    if direction=="LONG":
        accepted=signal.close>prior_high and signal.close>signal.open
    else:
        accepted=signal.close<prior_low and signal.close<signal.open
    if not accepted:return {"status":"NO_SIGNAL","reason":"no_confirmed_20bar_breakout"}
    atr=atr14(b15)
    if atr<=0:return {"status":"NO_SIGNAL","reason":"bad_atr"}
    return {"status":"PAPER_CANDIDATE","side":direction,
            "candle_close_utc":close_time.isoformat(),
            "signal_reference_close":signal.close,"indicative_stop_distance":1.5*atr,
            "research_target_R":2.0,
            "execution":"UNVERIFIED — no trade, no broker price"}

def allowed_risk_eur(equity,realized_daily_loss,loss_streak,positions):
    """No lot sizing; only maximum admissible EUR exposure, fail closed."""
    if any(not isfinite(v) for v in (equity,realized_daily_loss)) or equity<=0 or realized_daily_loss<0:
        raise ValueError("invalid equity/loss")
    if loss_streak<0 or positions<0:raise ValueError("invalid position state")
    if loss_streak>=2 or positions>=1:return 0.0
    return max(0.0,min(equity*0.005,equity*0.01-realized_daily_loss))
