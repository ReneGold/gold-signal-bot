"""Research-only XAU/USD entry timer: require completed 15m setup and optional 5m confirmation.
No orders and no Telegram messages. Times are timezone-aware UTC candle opening times.
"""
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from enum import Enum

class Status(str,Enum):
    WAITING="WAITING"
    CONFIRMED="CONFIRMED"
    EXPIRED="EXPIRED"
    INVALID="INVALID"

@dataclass(frozen=True)
class Candle:
    t: datetime
    o: float
    h: float
    l: float
    c: float

def assess_entry(*,setup_close_utc,side,trigger,invalid_level,five_minute_bars,
                 now_utc,confirmation_window_minutes=30):
    """The trigger must be crossed by a CLOSED 5m candle's close, not its high/low.
    Setup close is the close timestamp of an already completed 15m candle.
    No entry price/fill is promised; output is an alert eligibility decision only.
    """
    if side not in ("LONG","SHORT") or confirmation_window_minutes<=0 or confirmation_window_minutes%5:
        return dict(status=Status.INVALID.value,reason="Invalid parameters")
    if setup_close_utc.tzinfo is None or now_utc.tzinfo is None or now_utc<setup_close_utc:
        return dict(status=Status.INVALID.value,reason="Times must be aware and setup already closed")
    if not all(isinstance(v,(int,float)) and 0<v<float("inf") for v in (trigger,invalid_level)):
        return dict(status=Status.INVALID.value,reason="Invalid price")
    if (side=="LONG" and invalid_level>=trigger) or (side=="SHORT" and invalid_level<=trigger):
        return dict(status=Status.INVALID.value,reason="Invalid stop direction")
    until=setup_close_utc+timedelta(minutes=confirmation_window_minutes)
    for b in sorted(five_minute_bars,key=lambda x:x.t):
        if b.t.tzinfo is None:return dict(status=Status.INVALID.value,reason="Naive 5m time")
        closed=b.t+timedelta(minutes=5)
        if b.t<setup_close_utc or closed>now_utc or closed>until:continue
        if (side=="LONG" and b.c<=invalid_level) or (side=="SHORT" and b.c>=invalid_level):
            return dict(status=Status.INVALID.value,reason="Setup invalidated at 5m close",at_utc=closed.isoformat())
        confirmed=(b.c>trigger if side=="LONG" else b.c<trigger)
        if confirmed:
            return dict(status=Status.CONFIRMED.value,reason="Closed 5m candle confirmed",at_utc=closed.isoformat(),confirmation_close=b.c)
    if now_utc>=until:
        return dict(status=Status.EXPIRED.value,reason="Confirmation window ended")
    return dict(status=Status.WAITING.value,reason="Awaiting completed 5m confirmation")
