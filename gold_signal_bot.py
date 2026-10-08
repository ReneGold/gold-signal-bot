#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# GOLD DEMO BOT V3.8
# - nur Demo-Signale, KEINE automatischen Orders
# - Daten: Twelve Data
# - Ausgabe: Telegram
# - Basislogik aus dem bisherigen Bot + V3.8 Score-Filter
# =============================================================================

# --- Bestehende V3.7/V3.6-Basiswerte ---
FAST = 20
SLOW = 50
ATR_LEN = 14

ATR_BUF = 0.25
MAX_RISK_ATR = 1.75

TP1_R = 0.75
TP2_R = 1.50
TP3_R = 2.25

MIN_WICK_ATR = 0.40
SR_LEN = 20
ZONE_ATR = 0.35
MIN_PREMOVE_ATR = 1.00

TWEEZER_TOL = 0.15

BREAKOUT_LEN = 10
BREAKOUT_BUF = 0.10
BREAKOUT_BODY = 0.35
BREAKOUT_STOP_BARS = 3

MOM_LEN = 5
MOM_BODY = 0.35

MINTICK = 0.01

# --- V3.8 Score-Einstellungen ---
MIN_SCORE = int(os.getenv("MIN_SCORE", "70"))
HTF_INTERVAL = os.getenv("HTF_INTERVAL", "1h")
STRUCT_LEN = int(os.getenv("STRUCT_LEN", "6"))
LIQ_LEN = int(os.getenv("LIQ_LEN", "12"))
FVG_MAX_AGE = int(os.getenv("FVG_MAX_AGE", "12"))
FIB_LEN = int(os.getenv("FIB_LEN", "30"))
FIB_TOL_ATR = float(os.getenv("FIB_TOL_ATR", "0.15"))
MIN_ATR_PERCENT = float(os.getenv("MIN_ATR_PERCENT", "0.08"))

# --- Zugangsdaten / Laufzeit ---
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "").strip()
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "").strip()
SYMBOL = os.getenv("SYMBOL", "XAU/USD").strip()
STATE = Path(os.getenv("STATE_FILE", "state.json"))


@dataclass
class Candle:
    t: datetime
    o: float
    h: float
    l: float
    c: float


@dataclass
class Plan:
    direction: int
    signal_time: str
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    signal_type: str
    pattern: str
    score: int = 0
    score_detail: str = ""
    tp1_hit: bool = False
    tp2_hit: bool = False


def send(msg: str):
    """Telegram senden; ohne Telegram-Daten nur im Terminal ausgeben."""
    print(msg)
    if not TG_TOKEN or not TG_CHAT:
        return

    r = requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT, "text": msg},
        timeout=20,
    )
    if not r.ok:
        raise RuntimeError("Telegram: " + r.text)


def load_state():
    if not STATE.exists():
        return {"last_processed": None, "plan": None}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"last_processed": None, "plan": None}


def save_state(state):
    STATE.write_text(
        json.dumps(state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _interval_delta(interval: str) -> timedelta:
    if interval.endswith("min"):
        return timedelta(minutes=int(interval[:-3]))
    if interval.endswith("h"):
        return timedelta(hours=int(interval[:-1]))
    raise ValueError(f"Nicht unterstütztes Intervall: {interval}")


def candles(interval: str = "15min", outputsize: int = 300) -> list[Candle]:
    """Nur vollständig abgeschlossene Kerzen zurückgeben."""
    if not API_KEY:
        raise RuntimeError("TWELVE_DATA_API_KEY fehlt in .env")

    r = requests.get(
        "https://api.twelvedata.com/time_series",
        params={
            "symbol": SYMBOL,
            "interval": interval,
            "outputsize": outputsize,
            "timezone": "UTC",
            "format": "JSON",
            "apikey": API_KEY,
        },
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()

    if data.get("status") == "error":
        raise RuntimeError(data.get("message", str(data)))

    out: list[Candle] = []
    for x in data.get("values", []):
        t = datetime.fromisoformat(x["datetime"])
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        else:
            t = t.astimezone(timezone.utc)

        out.append(
            Candle(
                t=t,
                o=float(x["open"]),
                h=float(x["high"]),
                l=float(x["low"]),
                c=float(x["close"]),
            )
        )

    out.sort(key=lambda x: x.t)

    delta = _interval_delta(interval)
    now = datetime.now(timezone.utc)

    # Kleiner Puffer, damit nur sicher geschlossene Kerzen verarbeitet werden.
    return [x for x in out if x.t + delta + timedelta(seconds=20) <= now]


def ema(values: list[float], n: int) -> list[float]:
    a = 2 / (n + 1)
    out = []
    e = values[0]
    for x in values:
        e = a * x + (1 - a) * e
        out.append(e)
    return out


def rma(values: list[float], n: int) -> list[Optional[float]]:
    out: list[Optional[float]] = [None] * len(values)
    if len(values) < n:
        return out

    p = sum(values[:n]) / n
    out[n - 1] = p

    for i in range(n, len(values)):
        p = (values[i] + (n - 1) * p) / n
        out[i] = p

    return out


def indicators(c: list[Candle]):
    closes = [x.c for x in c]
    ef = ema(closes, FAST)
    es = ema(closes, SLOW)

    tr = []
    for i, x in enumerate(c):
        if i == 0:
            tr.append(x.h - x.l)
        else:
            tr.append(
                max(
                    x.h - x.l,
                    abs(x.h - c[i - 1].c),
                    abs(x.l - c[i - 1].c),
                )
            )

    return ef, es, rma(tr, ATR_LEN)


def htf_context_at(htf: list[Candle], signal_time: datetime):
    """
    Nimmt die letzte 1H-Kerze, die zum Zeitpunkt der 15M-Signalkerze
    bereits vollständig geschlossen war.
    """
    delta = _interval_delta(HTF_INTERVAL)
    eligible = [x for x in htf if x.t + delta <= signal_time]

    if len(eligible) < SLOW + 2:
        return False, False

    closes = [x.c for x in eligible]
    ef = ema(closes, FAST)
    es = ema(closes, SLOW)

    return (
        closes[-1] > ef[-1] and ef[-1] > es[-1],
        closes[-1] < ef[-1] and ef[-1] < es[-1],
    )


def _recent_fvg(c: list[Candle], i: int, bullish: bool):
    """
    Letztes klassisches 3-Kerzen-FVG bis zur aktuellen Kerze suchen.
    Rückgabe: (untere Zone, obere Zone, Alter) oder None.
    """
    start = max(2, i - FVG_MAX_AGE)

    for j in range(i, start - 1, -1):
        if bullish:
            if c[j].l > c[j - 2].h:
                return c[j - 2].h, c[j].l, i - j
        else:
            if c[j].h < c[j - 2].l:
                return c[j].h, c[j - 2].l, i - j

    return None


def signal(c, ef, es, atr, htf, i):
    if i < 80 or atr[i] is None:
        return None

    A = atr
    ai = A[i]
    if ai is None:
        return None

    body = lambda j: max(abs(c[j].c - c[j].o), MINTICK)

    # -------------------------------------------------------------------------
    # Bestehende V3.7-Basislogik
    # -------------------------------------------------------------------------
    b1, b2, b3 = body(i - 1), body(i - 2), body(i - 3)

    lw = min(c[i - 1].o, c[i - 1].c) - c[i - 1].l
    uw = c[i - 1].h - max(c[i - 1].o, c[i - 1].c)

    hammer = lw >= 2 * b1 and uw <= b1 and lw >= A[i - 1] * MIN_WICK_ATR
    shooting = uw >= 2 * b1 and lw <= b1 and uw >= A[i - 1] * MIN_WICK_ATR

    bull_eng = (
        c[i - 2].c < c[i - 2].o
        and c[i - 1].c > c[i - 1].o
        and c[i - 1].o <= c[i - 2].c
        and c[i - 1].c >= c[i - 2].o
    )
    bear_eng = (
        c[i - 2].c > c[i - 2].o
        and c[i - 1].c < c[i - 1].o
        and c[i - 1].o >= c[i - 2].c
        and c[i - 1].c <= c[i - 2].o
    )

    morning = (
        c[i - 3].c < c[i - 3].o
        and b3 >= A[i - 3] * 0.45
        and b2 <= b3 * 0.55
        and b2 <= A[i - 2] * 0.35
        and c[i - 1].c > c[i - 1].o
        and b1 >= A[i - 1] * 0.30
        and c[i - 1].c >= (c[i - 3].o + c[i - 3].c) / 2
    )
    evening = (
        c[i - 3].c > c[i - 3].o
        and b3 >= A[i - 3] * 0.45
        and b2 <= b3 * 0.55
        and b2 <= A[i - 2] * 0.35
        and c[i - 1].c < c[i - 1].o
        and b1 >= A[i - 1] * 0.30
        and c[i - 1].c <= (c[i - 3].o + c[i - 3].c) / 2
    )

    tw_bot = (
        c[i - 2].c < c[i - 2].o
        and c[i - 1].c > c[i - 1].o
        and abs(c[i - 1].l - c[i - 2].l) <= A[i - 1] * TWEEZER_TOL
        and c[i - 1].c >= (c[i - 2].o + c[i - 2].c) / 2
    )
    tw_top = (
        c[i - 2].c > c[i - 2].o
        and c[i - 1].c < c[i - 1].o
        and abs(c[i - 1].h - c[i - 2].h) <= A[i - 1] * TWEEZER_TOL
        and c[i - 1].c <= (c[i - 2].o + c[i - 2].c) / 2
    )

    bull = hammer or bull_eng or morning or tw_bot
    bear = shooting or bear_eng or evening or tw_top

    bull_name = (
        "MORNING STAR"
        if morning
        else "TWEEZER BOTTOM"
        if tw_bot
        else "BULL ENGULF"
        if bull_eng
        else "HAMMER"
        if hammer
        else "WENDE"
    )
    bear_name = (
        "EVENING STAR"
        if evening
        else "TWEEZER TOP"
        if tw_top
        else "BEAR ENGULF"
        if bear_eng
        else "SHOOTING STAR"
        if shooting
        else "WENDE"
    )

    patt_low = min(c[i - 1].l, c[i - 2].l, c[i - 3].l)
    patt_high = max(c[i - 1].h, c[i - 2].h, c[i - 3].h)

    s0 = i - 4 - SR_LEN + 1
    support = min(x.l for x in c[s0 : i - 3])
    resist = max(x.h for x in c[s0 : i - 3])

    near_sup = patt_low <= support + A[i - 1] * ZONE_ATR
    near_res = patt_high >= resist - A[i - 1] * ZONE_ATR
    near_ema = abs(c[i - 1].c - es[i - 1]) <= A[i - 1] * ZONE_ATR

    prev_down = c[i - 6].c - c[i - 1].c >= A[i - 1] * MIN_PREMOVE_ATR
    prev_up = c[i - 1].c - c[i - 6].c >= A[i - 1] * MIN_PREMOVE_ATR

    long_ctx = near_sup or (near_ema and prev_down) or (prev_down and (morning or tw_bot))
    short_ctx = near_res or (near_ema and prev_up) or (prev_up and (evening or tw_top))

    up = ef[i] > es[i] and c[i].c > ef[i]
    down = ef[i] < es[i] and c[i].c < ef[i]

    was_down = ef[i - 1] < ef[i - 3] and c[i - 1].c < es[i - 1]
    was_up = ef[i - 1] > ef[i - 3] and c[i - 1].c > es[i - 1]

    lc = bull and c[i].c > c[i - 1].h and c[i].c > c[i].o
    sc = bear and c[i].c < c[i - 1].l and c[i].c < c[i].o

    lt = lc and up
    st = sc and down
    le = lc and was_down and long_ctx and not lt
    se = sc and was_up and short_ctx and not st

    bh = max(x.h for x in c[i - BREAKOUT_LEN : i])
    bl = min(x.l for x in c[i - BREAKOUT_LEN : i])
    cur_body = abs(c[i].c - c[i].o)

    pbh = max(x.h for x in c[i - 1 - BREAKOUT_LEN : i - 1])
    pbl = min(x.l for x in c[i - 1 - BREAKOUT_LEN : i - 1])

    lb = (
        up
        and ef[i] > ef[i - 1]
        and c[i].c > c[i].o
        and cur_body >= ai * BREAKOUT_BODY
        and c[i].c > bh + ai * BREAKOUT_BUF
        and c[i - 1].c <= pbh + A[i - 1] * BREAKOUT_BUF
    )
    sb = (
        down
        and ef[i] < ef[i - 1]
        and c[i].c < c[i].o
        and cur_body >= ai * BREAKOUT_BODY
        and c[i].c < bl - ai * BREAKOUT_BUF
        and c[i - 1].c >= pbl - A[i - 1] * BREAKOUT_BUF
    )

    mh = max(x.h for x in c[i - MOM_LEN : i])
    ml = min(x.l for x in c[i - MOM_LEN : i])

    lm = (
        not le
        and ef[i] <= es[i]
        and ef[i] > ef[i - 1]
        and ef[i - 1] >= ef[i - 2]
        and (es[i] - ef[i]) < (es[i - 2] - ef[i - 2])
        and c[i].c > es[i]
        and c[i].c > mh
        and c[i].c > c[i].o
        and cur_body >= ai * MOM_BODY
    )
    sm = (
        not se
        and ef[i] >= es[i]
        and ef[i] < ef[i - 1]
        and ef[i - 1] <= ef[i - 2]
        and (ef[i] - es[i]) < (ef[i - 2] - es[i - 2])
        and c[i].c < es[i]
        and c[i].c < ml
        and c[i].c < c[i].o
        and cur_body >= ai * MOM_BODY
    )

    long_base = lt or le or lb or lm
    short_base = st or se or sb or sm

    if not long_base and not short_base:
        return None

    # -------------------------------------------------------------------------
    # V3.8 Zusatzfilter / Score
    # -------------------------------------------------------------------------
    htf_bull, htf_bear = htf_context_at(htf, c[i].t)

    sh_now = max(x.h for x in c[i - STRUCT_LEN + 1 : i + 1])
    sl_now = min(x.l for x in c[i - STRUCT_LEN + 1 : i + 1])
    sh_prev = max(x.h for x in c[i - 2 * STRUCT_LEN + 1 : i - STRUCT_LEN + 1])
    sl_prev = min(x.l for x in c[i - 2 * STRUCT_LEN + 1 : i - STRUCT_LEN + 1])

    structure_bull = sh_now > sh_prev and sl_now > sl_prev
    structure_bear = sh_now < sh_prev and sl_now < sl_prev

    bos_ref_high = max(x.h for x in c[i - STRUCT_LEN : i])
    bos_ref_low = min(x.l for x in c[i - STRUCT_LEN : i])

    prev_bos_ref_high = max(x.h for x in c[i - 1 - STRUCT_LEN : i - 1])
    prev_bos_ref_low = min(x.l for x in c[i - 1 - STRUCT_LEN : i - 1])

    bull_bos = c[i].c > bos_ref_high and c[i - 1].c <= prev_bos_ref_high
    bear_bos = c[i].c < bos_ref_low and c[i - 1].c >= prev_bos_ref_low

    bull_choch = bull_bos and (
        max(x.h for x in c[i - 1 - STRUCT_LEN + 1 : i])
        < max(x.h for x in c[i - 1 - 2 * STRUCT_LEN + 1 : i - 1 - STRUCT_LEN + 1])
        and min(x.l for x in c[i - 1 - STRUCT_LEN + 1 : i])
        < min(x.l for x in c[i - 1 - 2 * STRUCT_LEN + 1 : i - 1 - STRUCT_LEN + 1])
    )
    bear_choch = bear_bos and (
        max(x.h for x in c[i - 1 - STRUCT_LEN + 1 : i])
        > max(x.h for x in c[i - 1 - 2 * STRUCT_LEN + 1 : i - 1 - STRUCT_LEN + 1])
        and min(x.l for x in c[i - 1 - STRUCT_LEN + 1 : i])
        > min(x.l for x in c[i - 1 - 2 * STRUCT_LEN + 1 : i - 1 - STRUCT_LEN + 1])
    )

    liq_high = max(x.h for x in c[i - LIQ_LEN : i])
    liq_low = min(x.l for x in c[i - LIQ_LEN : i])

    long_sweep = c[i].l < liq_low and c[i].c > liq_low
    short_sweep = c[i].h > liq_high and c[i].c < liq_high

    bull_fvg = _recent_fvg(c, i, bullish=True)
    bear_fvg = _recent_fvg(c, i, bullish=False)

    long_fvg_ok = False
    if bull_fvg:
        lower, upper, _ = bull_fvg
        long_fvg_ok = c[i].l <= upper + ai * 0.10 and c[i].c >= lower

    short_fvg_ok = False
    if bear_fvg:
        lower, upper, _ = bear_fvg
        short_fvg_ok = c[i].h >= lower - ai * 0.10 and c[i].c <= upper

    fib_high = max(x.h for x in c[i - FIB_LEN : i])
    fib_low = min(x.l for x in c[i - FIB_LEN : i])
    fib_range = max(fib_high - fib_low, MINTICK)

    fib_long_50 = fib_high - fib_range * 0.500
    fib_long_786 = fib_high - fib_range * 0.786

    fib_short_50 = fib_low + fib_range * 0.500
    fib_short_786 = fib_low + fib_range * 0.786

    long_fib_ok = (
        c[i].c <= fib_long_50 + ai * FIB_TOL_ATR
        and c[i].c >= fib_long_786 - ai * FIB_TOL_ATR
    )
    short_fib_ok = (
        c[i].c >= fib_short_50 - ai * FIB_TOL_ATR
        and c[i].c <= fib_short_786 + ai * FIB_TOL_ATR
    )

    bull_candle_quality = lc or (c[i].c > c[i].o and cur_body >= ai * 0.30)
    bear_candle_quality = sc or (c[i].c < c[i].o and cur_body >= ai * 0.30)

    momentum_long_ok = ef[i] > ef[i - 1] and c[i].c > c[i - 1].c
    momentum_short_ok = ef[i] < ef[i - 1] and c[i].c < c[i - 1].c

    atr_percent = ai / c[i].c * 100.0 if c[i].c else 0.0
    volatility_ok = atr_percent >= MIN_ATR_PERCENT

    long_score = 0
    long_score += 15 if htf_bull else 0
    long_score += 15 if structure_bull else 0
    long_score += 10 if (bull_bos or bull_choch) else 0
    long_score += 10 if long_sweep else 0
    long_score += 10 if long_fvg_ok else 0
    long_score += 10 if long_fib_ok else 0
    long_score += 10 if bull_candle_quality else 0
    long_score += 10 if momentum_long_ok else 0
    long_score += 5 if up else 0
    long_score += 5 if volatility_ok else 0

    short_score = 0
    short_score += 15 if htf_bear else 0
    short_score += 15 if structure_bear else 0
    short_score += 10 if (bear_bos or bear_choch) else 0
    short_score += 10 if short_sweep else 0
    short_score += 10 if short_fvg_ok else 0
    short_score += 10 if short_fib_ok else 0
    short_score += 10 if bear_candle_quality else 0
    short_score += 10 if momentum_short_ok else 0
    short_score += 5 if down else 0
    short_score += 5 if volatility_ok else 0

    # Bei gleichzeitigen Kandidaten nur die stärkere Seite zulassen.
    long_ok = long_base and long_score >= MIN_SCORE
    short_ok = short_base and short_score >= MIN_SCORE

    if long_ok and short_ok:
        if long_score > short_score:
            short_ok = False
        elif short_score > long_score:
            long_ok = False
        else:
            return None

    # -------------------------------------------------------------------------
    # Stops / Ziele unverändert nach bestehender Logik
    # -------------------------------------------------------------------------
    lstop_turn = min(c[i].l, c[i - 1].l) - ai * ATR_BUF
    sstop_turn = max(c[i].h, c[i - 1].h) + ai * ATR_BUF

    lstop_br = (
        min(min(x.l for x in c[i - BREAKOUT_STOP_BARS + 1 : i + 1]), bh)
        - ai * ATR_BUF
    )
    sstop_br = (
        max(max(x.h for x in c[i - BREAKOUT_STOP_BARS + 1 : i + 1]), bl)
        + ai * ATR_BUF
    )

    lstop_m = min(x.l for x in c[i - 2 : i + 1]) - ai * ATR_BUF
    sstop_m = max(x.h for x in c[i - 2 : i + 1]) + ai * ATR_BUF

    if long_ok:
        sl = lstop_m if lm else lstop_br if lb else lstop_turn
        risk = c[i].c - sl

        if MINTICK < risk <= ai * MAX_RISK_ATR:
            typ = (
                "MOMENTUM-WENDE"
                if lm
                else "AUSBRUCH"
                if lb
                else ("FRUEH / " + bull_name)
                if le
                else ("TRENDFOLGE / " + bull_name)
            )
            pat = "Momentum-Wende" if lm else "Ausbruch" if lb else bull_name

            detail = (
                f"1H={'LONG' if htf_bull else 'neutral'} | "
                f"Struktur={'HH/HL' if structure_bull else 'nein'} | "
                f"BOS/CHoCH={'ja' if (bull_bos or bull_choch) else 'nein'} | "
                f"Sweep={'ja' if long_sweep else 'nein'} | "
                f"FVG={'ja' if long_fvg_ok else 'nein'} | "
                f"Fib={'ja' if long_fib_ok else 'nein'}"
            )

            return (
                1,
                c[i].c,
                sl,
                c[i].c + TP1_R * risk,
                c[i].c + TP2_R * risk,
                c[i].c + TP3_R * risk,
                typ,
                pat,
                long_score,
                detail,
            )

    if short_ok:
        sl = sstop_m if sm else sstop_br if sb else sstop_turn
        risk = sl - c[i].c

        if MINTICK < risk <= ai * MAX_RISK_ATR:
            typ = (
                "MOMENTUM-WENDE"
                if sm
                else "AUSBRUCH"
                if sb
                else ("FRUEH / " + bear_name)
                if se
                else ("TRENDFOLGE / " + bear_name)
            )
            pat = "Momentum-Wende" if sm else "Ausbruch" if sb else bear_name

            detail = (
                f"1H={'SHORT' if htf_bear else 'neutral'} | "
                f"Struktur={'LH/LL' if structure_bear else 'nein'} | "
                f"BOS/CHoCH={'ja' if (bear_bos or bear_choch) else 'nein'} | "
                f"Sweep={'ja' if short_sweep else 'nein'} | "
                f"FVG={'ja' if short_fvg_ok else 'nein'} | "
                f"Fib={'ja' if short_fib_ok else 'nein'}"
            )

            return (
                -1,
                c[i].c,
                sl,
                c[i].c - TP1_R * risk,
                c[i].c - TP2_R * risk,
                c[i].c - TP3_R * risk,
                typ,
                pat,
                short_score,
                detail,
            )

    return None


def fmt(x):
    return f"{x:.2f}"


def new_plan_message(p: Plan):
    side = "KAUF / LONG" if p.direction == 1 else "VERKAUF / SHORT"
    icon = "🟢" if p.direction == 1 else "🔴"

    return (
        f"{icon} GOLD DEMO V3.8 – {side}\n"
        f"Score: {p.score}/100\n"
        f"Signal: {p.signal_type}\n"
        f"Muster: {p.pattern}\n"
        f"{p.score_detail}\n"
        f"Einstieg: {fmt(p.entry)}\n"
        f"Stop-Loss: {fmt(p.sl)}\n"
        f"TP1: {fmt(p.tp1)}\n"
        f"TP2: {fmt(p.tp2)}\n"
        f"TP3: {fmt(p.tp3)}\n"
        f"Zeitrahmen: 15 Minuten | Trendfilter: {HTF_INTERVAL}\n"
        f"Kerze: {p.signal_time}\n"
        f"Hinweis: Demo-Signal, keine Garantie."
    )


def process(c, ef, es, atr, htf, i, state):
    just_finished = False

    if state.get("plan"):
        # Rückwärtskompatibel: ältere State-Dateien dürfen score-Felder noch nicht haben.
        plan_data = dict(state["plan"])
        plan_data.setdefault("score", 0)
        plan_data.setdefault("score_detail", "")
        plan_data.setdefault("tp1_hit", False)
        plan_data.setdefault("tp2_hit", False)

        p = Plan(**plan_data)
        b = c[i]

        protective = p.tp1 if p.tp2_hit else p.entry if p.tp1_hit else p.sl

        stop = b.l <= protective if p.direction == 1 else b.h >= protective
        h3 = b.h >= p.tp3 if p.direction == 1 else b.l <= p.tp3
        h2 = b.h >= p.tp2 if p.direction == 1 else b.l <= p.tp2
        h1 = b.h >= p.tp1 if p.direction == 1 else b.l <= p.tp1

        # Konservativ: wenn Stop und Ziel in derselben Kerze liegen, Stop zuerst.
        if stop:
            send(
                f"🛑 GOLD DEMO V3.8 – STOP\n"
                f"Schutz-Stop: {fmt(protective)}\n"
                f"Plan beendet."
            )
            state["plan"] = None
            just_finished = True

        elif h3:
            send(
                f"✅ GOLD DEMO V3.8 – TP3 erreicht\n"
                f"TP3: {fmt(p.tp3)}\n"
                f"Plan abgeschlossen."
            )
            state["plan"] = None
            just_finished = True

        else:
            if h2 and not p.tp2_hit:
                p.tp1_hit = True
                p.tp2_hit = True
                send(
                    f"✅ GOLD DEMO V3.8 – TP2 erreicht\n"
                    f"TP2: {fmt(p.tp2)}\n"
                    f"Schutz-Stop ab nächster Kerze auf TP1: {fmt(p.tp1)}"
                )

            elif h1 and not p.tp1_hit:
                p.tp1_hit = True
                send(
                    f"✅ GOLD DEMO V3.8 – TP1 erreicht\n"
                    f"TP1: {fmt(p.tp1)}\n"
                    f"Schutz-Stop ab nächster Kerze auf Einstieg: {fmt(p.entry)}"
                )

            state["plan"] = asdict(p)

    if state.get("plan") is None and not just_finished:
        s = signal(c, ef, es, atr, htf, i)

        if s:
            p = Plan(
                direction=s[0],
                signal_time=c[i].t.isoformat(),
                entry=s[1],
                sl=s[2],
                tp1=s[3],
                tp2=s[4],
                tp3=s[5],
                signal_type=s[6],
                pattern=s[7],
                score=s[8],
                score_detail=s[9],
            )
            state["plan"] = asdict(p)
            send(new_plan_message(p))


def run_once():
    c = candles("15min", 320)
    htf = candles(HTF_INTERVAL, 220)

    if len(c) < 100:
        raise RuntimeError(f"Zu wenige 15M-Kerzen: {len(c)}")
    if len(htf) < SLOW + 5:
        raise RuntimeError(f"Zu wenige {HTF_INTERVAL}-Kerzen: {len(htf)}")

    ef, es, atr = indicators(c)

    state = load_state()
    last = state.get("last_processed")

    now_utc = datetime. now(timezone.utc)

closed_idx = [
    i for i, x in enumerate(c)
    if x.t + timedelta(minutes=15) <= now_utc
]

if not closed_idx:
    idx = []
else:
    latest_i = closed_idx[-1]
    latest_time = c[latest_i].t.isoformat()

    if last and latest_time <= last:
        idx = []
    else:
        idx = [latest_i]

    for i in idx:
        process(c, ef, es, atr, htf, i, state)
        state["last_processed"] = c[i].t.isoformat()
        save_state(state)

    print(
        datetime.now().isoformat(timespec="seconds"),
        "-",
        len(idx),
        "neue Kerze(n)",
    )


def wait_seconds():
    now = datetime.now(timezone.utc)
    mins = 15 - (now.minute % 15)
    nxt = now.replace(second=0, microsecond=0) + timedelta(
        minutes=mins,
        seconds=25,
    )
    return max(20, int((nxt - now).total_seconds()))


def main():
    print(
        f"Gold Signal Bot V3.8 gestartet – keine automatischen Orders. "
        f"MIN_SCORE={MIN_SCORE}"
    )

    # GitHub Actions: genau einmal prüfen.
    # Mac: dauerhaft weiterlaufen.
    one_shot = (
        os.getenv("GITHUB_ACTIONS", "").lower() == "true"
        or os.getenv("RUN_ONCE", "").lower() in ("1", "true", "yes")
    )

    if one_shot:
        try:
            run_once()
        except Exception as e:
            print("FEHLER:", e)
            try:
                send("⚠️ Gold Signal Bot V3.8 Fehler: " + str(e))
            except Exception:
                pass
            raise
        return

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print("FEHLER:", e)
            try:
                send("⚠️ Gold Signal Bot V3.8 Fehler: " + str(e))
            except Exception:
                pass

        time.sleep(wait_seconds())


if __name__ == "__main__":
    main()
