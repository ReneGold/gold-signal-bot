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

    result = signal(c, ef, es, atr, htf, target_i)

    print("SIGNAL-ERGEBNIS:")
    print(result)
