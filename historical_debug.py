import sys

from gold_signal_bot import candles, indicators, signal, HTF_INTERVAL

TARGET = "2026-10-13T03:45:00+00:00"

c = candles("15min", 320)
htf = candles(HTF_INTERVAL, 220)

ef, es, atr = indicators(c)

target_i = None

for i, candle in enumerate(c):
    if candle.t.isoformat() == TARGET:
        target_i = i
        break

if target_i is None:
    print("Zielkerze nicht gefunden:", TARGET)
else:
    print("Zielkerze gefunden:")
    print(
        target_i,
        c[target_i].t.isoformat(),
        "O=", c[target_i].o,
        "H=", c[target_i].h,
        "L=", c[target_i].l,
        "C=", c[target_i].c,
    )

    captured = {}

    def tracer(frame, event, arg):
        if frame.f_code.co_name == "signal" and event == "return":
            captured.update(frame.f_locals.copy())
        return tracer

    sys.settrace(tracer)
    try:
        result = signal(c, ef, es, atr, htf, target_i)
    finally:
        sys.settrace(None)

    print("\nSIGNAL-ERGEBNIS:")
    print(result)

    keys = [
        "lt", "le", "lb", "lm",
        "st", "se", "sb", "sm",
        "long_base", "short_base",
        "long_score", "short_score",
        "htf_bull", "htf_bear",
        "structure_bull", "structure_bear",
        "bull_bos", "bull_choch", "bull_retest",
        "bear_bos", "bear_choch", "bear_retest",
        "long_sweep", "short_sweep",
        "long_fvg_ok", "short_fvg_ok",
        "long_fib_ok", "short_fib_ok",
        "bull_candle_quality", "bear_candle_quality",
        "momentum_long_ok", "momentum_short_ok",
        "up", "down",
        "volatility_ok", "atr_percent",
        "adx_now", "range_market", "range_atr_ratio",
        "long_ok", "short_ok", "long_watch", "short_watch",
        "bh", "bl", "pbh", "pbl", "cur_body", "ai",
    ]

    print("\nDEBUG HISTORISCH:")
    for key in keys:
        if key in captured:
            print(f"{key}={captured[key]}")

    print("\nWICHTIG:")
    print("Der Produktionsbot wird durch diesen Test nicht veraendert und sendet keinen Trade.")


# Zusatz: Python-HTF-Werte fuer den Vergleich mit TradingView
from gold_signal_bot import ema, FAST, SLOW, _interval_delta

if target_i is not None:
    signal_time = c[target_i].t
    delta = _interval_delta(HTF_INTERVAL)
    eligible = [x for x in htf if x.t + delta <= signal_time]
    if len(eligible) >= SLOW + 2:
        htf_closes = [x.c for x in eligible]
        htf_fast = ema(htf_closes, FAST)
        htf_slow = ema(htf_closes, SLOW)
        print("\nPYTHON HTF DETAILS:")
        print("htf_time=", eligible[-1].t.isoformat())
        print("htf_close=", htf_closes[-1])
        print("htf_ema_fast=", htf_fast[-1])
        print("htf_ema_slow=", htf_slow[-1])
        print("htf_bull_calc=", htf_closes[-1] > htf_fast[-1] and htf_fast[-1] > htf_slow[-1])


# HTF HISTORY WARMUP TEST:
# TradingView berechnet EMA ueber sehr viel mehr Historie als die 220 Stunden,
# die der Bot bisher laedt. Wir pruefen, ob genau das die 15 Punkte Differenz erklaert.
print("\nHTF HISTORY WARMUP TEST:")
for size in (220, 500, 1000, 2000):
    try:
        htf_test = candles(HTF_INTERVAL, size)
        eligible_test = [x for x in htf_test if x.t + _interval_delta(HTF_INTERVAL) <= c[target_i].t]
        if len(eligible_test) < SLOW + 2:
            print(f"size={size}: zu wenig Daten ({len(eligible_test)})")
            continue
        closes_test = [x.c for x in eligible_test]
        fast_test = ema(closes_test, FAST)[-1]
        slow_test = ema(closes_test, SLOW)[-1]
        close_test = closes_test[-1]
        bull_test = close_test > fast_test and fast_test > slow_test
        print(
            f"size={size} | candles={len(eligible_test)} | "
            f"close={close_test:.5f} | fast={fast_test:.5f} | "
            f"slow={slow_test:.5f} | htf_bull={bull_test}"
        )
    except Exception as e:
        print(f"size={size}: FEHLER {e}")
