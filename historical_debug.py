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
from gold_signal_bot import ema, rma, FAST, SLOW, ATR_LEN, _interval_delta

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


# HTF TOLERANCE TEST:
# Testet, wie viel Toleranz zwischen EMA Fast und EMA Slow noetig waere,
# damit die Beispielkerze als bullischer HTF-Kontext gilt.
print("\nHTF TOLERANCE TEST:")
if target_i is not None:
    signal_time = c[target_i].t
    delta = _interval_delta(HTF_INTERVAL)
    eligible_tol = [x for x in htf if x.t + delta <= signal_time]
    if len(eligible_tol) >= SLOW + 2:
        closes_tol = [x.c for x in eligible_tol]
        ef_tol = ema(closes_tol, FAST)
        es_tol = ema(closes_tol, SLOW)

        # 1H ATR berechnen
        tr_tol = []
        for j, x in enumerate(eligible_tol):
            if j == 0:
                tr_tol.append(x.h - x.l)
            else:
                tr_tol.append(max(
                    x.h - x.l,
                    abs(x.h - eligible_tol[j - 1].c),
                    abs(x.l - eligible_tol[j - 1].c),
                ))
        atr_tol_series = rma(tr_tol, ATR_LEN)
        atr1h = atr_tol_series[-1]

        gap = es_tol[-1] - ef_tol[-1]
        print(f"ema_gap_slow_minus_fast={gap:.5f}")
        print(f"atr_1h={atr1h:.5f}" if atr1h is not None else "atr_1h=None")

        for frac in (0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
            if atr1h is None:
                break
            tol = atr1h * frac
            bull_relaxed = closes_tol[-1] > ef_tol[-1] and ef_tol[-1] >= es_tol[-1] - tol
            print(
                f"tol={frac:.2f} ATR | abs_tol={tol:.5f} | "
                f"htf_bull_relaxed={bull_relaxed}"
            )


# HTF PARTIAL SCORE TEST:
# Testet einen abgestuften HTF-Score statt nur 15 oder 0 Punkte.
# Idee:
# +15 = voll bullisch: Close > EMA Fast > EMA Slow
# +10 = Close > EMA Fast und EMA Fast steigt, aber noch unter EMA Slow
# +5  = Close > EMA Fast, EMA Fast noch nicht steigend
#  0  = sonst
print("\nHTF PARTIAL SCORE TEST:")
if target_i is not None:
    signal_time = c[target_i].t
    delta = _interval_delta(HTF_INTERVAL)
    eligible_ps = [x for x in htf if x.t + delta <= signal_time]

    if len(eligible_ps) >= SLOW + 3:
        closes_ps = [x.c for x in eligible_ps]
        ef_ps = ema(closes_ps, FAST)
        es_ps = ema(closes_ps, SLOW)

        full_bull = closes_ps[-1] > ef_ps[-1] and ef_ps[-1] > es_ps[-1]
        close_above_fast = closes_ps[-1] > ef_ps[-1]
        fast_rising = ef_ps[-1] > ef_ps[-2]

        if full_bull:
            htf_points = 15
        elif close_above_fast and fast_rising:
            htf_points = 10
        elif close_above_fast:
            htf_points = 5
        else:
            htf_points = 0

        revised_long_score = captured.get("long_score", 0) + htf_points

        print(f"full_bull={full_bull}")
        print(f"close_above_fast={close_above_fast}")
        print(f"fast_rising={fast_rising}")
        print(f"htf_partial_points={htf_points}")
        print(f"original_long_score={captured.get('long_score')}")
        print(f"revised_long_score={revised_long_score}")
        print(f"would_pass_min_score={revised_long_score >= 70}")


# ZONE SCORE TEST:
# Erste objektive Zonenbewertung 0-100 auf Basis bereits vorhandener Bot-Faktoren.
# Noch KEINE Aenderung am Produktionsbot.
print("\nZONE SCORE TEST:")
if target_i is not None:
    # Werte stammen direkt aus signal()-Lokalspeicher des historischen Tests.
    long_zone_score = 0
    short_zone_score = 0

    # Naehe zu Support/Resistance: 25 Punkte
    if captured.get("near_sup"):
        long_zone_score += 25
    if captured.get("near_res"):
        short_zone_score += 25

    # Naehe zur langsamen EMA: 15 Punkte
    if captured.get("near_ema"):
        long_zone_score += 15
        short_zone_score += 15

    # FVG-Reaktion: 20 Punkte
    if captured.get("long_fvg_ok"):
        long_zone_score += 20
    if captured.get("short_fvg_ok"):
        short_zone_score += 20

    # Fibonacci-Reaktionszone: 15 Punkte
    if captured.get("long_fib_ok"):
        long_zone_score += 15
    if captured.get("short_fib_ok"):
        short_zone_score += 15

    # Liquidity Sweep: 15 Punkte
    if captured.get("long_sweep"):
        long_zone_score += 15
    if captured.get("short_sweep"):
        short_zone_score += 15

    # BOS/CHoCH-Retest: 10 Punkte
    if captured.get("bull_retest"):
        long_zone_score += 10
    if captured.get("bear_retest"):
        short_zone_score += 10

    print(f"long_zone_score={long_zone_score}")
    print(f"short_zone_score={short_zone_score}")
    print(
        "long_zone_grade=" +
        ("A" if long_zone_score >= 75 else
         "B" if long_zone_score >= 55 else
         "C" if long_zone_score >= 35 else
         "D")
    )
    print(
        "short_zone_grade=" +
        ("A" if short_zone_score >= 75 else
         "B" if short_zone_score >= 55 else
         "C" if short_zone_score >= 35 else
         "D")
    )
    print("ZONE SCORE DETAILS:")
    for key in (
        "near_sup", "near_res", "near_ema",
        "long_fvg_ok", "short_fvg_ok",
        "long_fib_ok", "short_fib_ok",
        "long_sweep", "short_sweep",
        "bull_retest", "bear_retest",
    ):
        if key in captured:
            print(f"{key}={captured[key]}")


# SESSION + SETUP GRADE TEST:
# Nur Anzeige-Test, keine Aenderung am Produktionsbot.
from zoneinfo import ZoneInfo

def debug_setup_grade(score: int) -> str:
    if score >= 90:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 80:
        return "A-"
    if score >= 75:
        return "B+"
    if score >= 70:
        return "B"
    return "C"

def debug_session(dt):
    london = dt.astimezone(ZoneInfo("Europe/London"))
    new_york = dt.astimezone(ZoneInfo("America/New_York"))
    tokyo = dt.astimezone(ZoneInfo("Asia/Tokyo"))

    london_min = london.hour * 60 + london.minute
    ny_min = new_york.hour * 60 + new_york.minute
    tokyo_min = tokyo.hour * 60 + tokyo.minute

    london_active = 8 * 60 <= london_min < 16 * 60 + 30
    ny_active = 8 * 60 <= ny_min < 17 * 60
    asia_active = 9 * 60 <= tokyo_min < 17 * 60

    if london_active and ny_active:
        return "LONDON / NEW YORK OVERLAP"
    if london_active:
        return "LONDON"
    if ny_active:
        return "NEW YORK"
    if asia_active:
        return "ASIA"
    return "OFF-HOURS"

print("\nSESSION + SETUP GRADE TEST:")
if target_i is not None:
    score_for_grade = 70
    print("session=", debug_session(c[target_i].t))
    print("setup_grade_70=", debug_setup_grade(score_for_grade))
    print("setup_grade_75=", debug_setup_grade(75))
    print("setup_grade_80=", debug_setup_grade(80))
    print("setup_grade_85=", debug_setup_grade(85))
