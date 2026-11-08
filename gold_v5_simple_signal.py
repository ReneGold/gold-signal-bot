#!/usr/bin/env python3
"""Gold V5 SIMPLE: pure, deterministic research signal logic. NO API, Telegram or orders.

Input bars are fully closed, ordered OHLC bars with UTC-aware opening times.
The H1 series must contain ONLY bars closed at the 15m signal decision time.
RISK is indicative: broker contract value/spread must be verified before sizing.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite

@dataclass(frozen=True)
class Bar:
    start: datetime
    open: float
    high: float
    low: float
    close: float

def validate(bars, minutes):
    if len(bars) < 60:
        raise ValueError("At least 60 closed bars required for EMA warmup")
    for i, bar in enumerate(bars):
        if bar.start.tzinfo is None or bar.start.utcoffset() is None:
            raise ValueError("UTC-aware timestamps required")
        if bar.start.utcoffset() != timedelta(0):
            raise ValueError("Normalize timestamps to UTC first")
        if not all(isfinite(v) and v > 0 for v in (bar.open, bar.high, bar.low, bar.close)):
            raise ValueError("Invalid OHLC price")
        if bar.low > min(bar.open, bar.close) or bar.high < max(bar.open, bar.close):
            raise ValueError("Inconsistent OHLC")
        if i:
            delta = bar.start - bars[i - 1].start
            if delta <= timedelta(0) or delta.total_seconds() % (minutes * 60) != 0:
                raise ValueError("Invalid, nonmonotonic candle timestamps")
    # Scheduled gold maintenance and weekends may cause historical gaps.
    # Only a gap immediately before the decision disables a setup.
    if bars[-1].start - bars[-2].start != timedelta(minutes=minutes):
        raise ValueError("Gap in latest candles: no signal")

def ema(values, period):
    alpha = 2 / (period + 1)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1 - alpha) * result[-1])
    return result

def atr14(bars):
    tr = [bars[0].high - bars[0].low]
    for bar, prev in zip(bars[1:], bars[:-1]):
        tr.append(max(bar.high - bar.low, abs(bar.high - prev.close), abs(bar.low - prev.close)))
    out = [None] * len(tr)
    if len(tr) < 14:
        return out
    out[13] = sum(tr[:14]) / 14
    for i in range(14, len(tr)):
        out[i] = (13 * out[i - 1] + tr[i]) / 14
    return out

def decide(b15, b60, as_of):
    """One signal only at close of latest 15m bar. H1 trend must align.
    Forbids open/future bars, stale H1, missing bars and weak confirmations.
    No multiple setups, discretionary scoring or intrabar triggers.
    """
    if as_of.tzinfo is None or as_of.utcoffset() != timedelta(0):
        raise ValueError("as_of must be timezone-aware UTC")
    validate(b15, 15)
    validate(b60, 60)
    signal_close = b15[-1].start + timedelta(minutes=15)
    if signal_close > as_of or as_of - signal_close > timedelta(minutes=15):
        return {"status":"NO_SIGNAL","reason":"STALE_OR_OPEN_BAR"}
    last_h1_close = b60[-1].start + timedelta(hours=1)
    if last_h1_close > signal_close or signal_close - last_h1_close >= timedelta(hours=1):
        return {"status":"NO_SIGNAL","reason":"H1_NOT_CLOSED_OR_STALE"}
    x20 = ema([b.close for b in b15],20)
    x50 = ema([b.close for b in b15],50)
    h20 = ema([b.close for b in b60],20)
    h50 = ema([b.close for b in b60],50)
    current, previous = b15[-1], b15[-2]
    up = x20[-1] > x50[-1] and x20[-1] > x20[-2] and h20[-1] > h50[-1] and h20[-1] > h20[-2]
    down = x20[-1] < x50[-1] and x20[-1] < x20[-2] and h20[-1] < h50[-1] and h20[-1] < h20[-2]
    if not (up or down):
        return {"status":"NO_SIGNAL","reason":"TREND_NOT_ALIGNED"}
    long_touch = previous.low <= x20[-2]
    short_touch = previous.high >= x20[-2]
    long_confirm = current.close > x20[-1] and current.close > previous.high and current.close > current.open
    short_confirm = current.close < x20[-1] and current.close < previous.low and current.close < current.open
    side = "LONG" if up and long_touch and long_confirm else "SHORT" if down and short_touch and short_confirm else None
    if side is None:
        return {"status":"NO_SIGNAL","reason":"PULLBACK_OR_CONFIRMATION_MISSING"}
    distance = atr14(b15)[-1]
    if distance is None or distance <= 0:
        return {"status":"NO_SIGNAL","reason":"INVALID_ATR"}
    risk_distance = 1.5 * distance
    # Reference from the CLOSED signal bar. Real entry is unknown until next bar/broker quote.
    return {"status":"CANDIDATE_PAPER_ONLY","side":side,
            "signal_close_utc":signal_close.isoformat(),
            "reference_close":current.close,"stop_distance":risk_distance,
            "planned_reward_multiple":2.0,
            "entry_status":"WAIT_FOR_NEXT_BAR_AND_BROKER_VALIDATION"}

def risk_budget(equity_eur, daily_loss_eur, consecutive_losses, open_positions):
    """Fail-closed risk budget in account EUR, NOT a lot/contract size."""
    if not isfinite(equity_eur) or equity_eur <= 0 or not isfinite(daily_loss_eur) or daily_loss_eur < 0:
        raise ValueError("Invalid equity or daily loss")
    if consecutive_losses >= 2 or open_positions >= 1:
        return 0.0
    if consecutive_losses < 0 or open_positions < 0:
        raise ValueError("Invalid state")
    return max(0.0, min(equity_eur * 0.005, equity_eur * 0.01 - daily_loss_eur))
