# Gold & Bitcoin V5 – getrennter Regime-Backtest (Forschungsmodus)

Diese Werkzeuge ergaenzen den bestehenden Chart-Schattenvergleich um einen konservativen **Trade-Simulationsvergleich**. Sie veraendern weder Pine-V5-Signale noch den Gold-Paper-Forward-Bot.

## Vergleich

- **Frozen**: zuletzt abgeschlossene 1h-Kerze mit |EMA20-EMA50| / ATR14 < 0,5
- **Strong**: derselbe Quotient >= 0,5 und der 1h-EMA-Trend in Richtung des 15m-Einstiegs
- Sonst gleiche 15m-Kriterien: EMA20/50-Trend + EMA20-Kontakt auf der vorherigen Kerze + bestaetigter Ausbruch am geschlossenen Signalbalken
- Gold mit angenaeherter Chicago-Referenzsession; Bitcoin 24/7, sofern der Kursanbieter durchgehend Daten liefert
- Richtungsabhaengiger Einstieg beim Open der nachfolgenden 15m-Kerze (keine Rueckdatierung)
- Stop 1,5 x ATR14, Ziel 2R, maximal 16 abgeschlossene Einstiegskerzen, Stop zuerst bei gleichzeitig beruehrtem SL/TP
- Nur eine Position gleichzeitig **pro Regime-Test**; Verlust/Profit in risiko-normalisierten R
- Kostenparameter: halber Spread je Seite, Slippage je Seite, zusaetzlicher Roundtrip-Betrag in **Kurs-Punkten**, nicht in EUR oder Prozent
- Gold und Bitcoin benoetigen **separat kalibrierte** Kosten; 0 ist nur ein optimistischer Grenzfall

## Erforderliche echte OHLC-Daten

Je Markt zwei CSV-Dateien: **15 Minuten** und **1 Stunde**. Header:
`timestamp,open,high,low,close`

Zeitstempel muessen ISO-8601 mit UTC/Offset sein, und den **Balkenbeginn** bezeichnen; Preise muessen vom selben, definierten Datenfeed stammen. Gold-Session-Gaps werden zugelassen, aber nicht gefuellt. **Luecken bei offenem simuliertem Trade fuehren absichtlich zum Abbruch**, da die Ausfuehrung sonst nicht valide modelliert werden kann.

Ein Beispiel fuer den manuellen Aufruf (nur nach Vorliegen der OHLC-Dateien):

```bash
python -m unittest -v test_gold_v5_regime_backtest.py
python gold_v5_regime_backtest.py --market gold \
  --bars15 gold_15m.csv --bars1h gold_1h.csv \
  --half-spread 0.15 --slippage 0.10 --cost 0.30 \
  --out gold_regime_result.json
python gold_v5_regime_backtest.py --market bitcoin \
  --bars15 bitcoin_15m.csv --bars1h bitcoin_1h.csv \
  --half-spread 2.0 --slippage 3.0 --cost 0 \
  --out bitcoin_regime_result.json
```

**Kostenwerte in den Beispielen sind frei gewaehlte Platzhalter und KEINE echten Brokerkonditionen.** Fuer belastbare Ergebnisse echte Spreads, Slippage, Gebuehren/Funding und korrekte Symbol-/Tickgroessen benutzen.

## Risiken und methodische Grenzen

- Historische Kurse koennen Zukunftswissen durch das **nachtraegliche Auswaehlen der besten Regel** erzeugen. Parameter zuerst auf Trainingsdaten festlegen, dann an unabhaengigen Zeitfenstern (Out-of-Sample) pruefen.
- Die Python-EMA initialisiert anders als moegliche TradingView-Datenfeeds; nur gleiche OHLC-Quelle und genuegend Warm-up erlauben fairen Vergleich. Die Stundendaten werden nur verwendet, wenn die H1-Kerze zum Entscheidungszeitpunkt schon abgeschlossen ist.
- Kein exakter 1:1-Abgleich zur alten Pine-Anzeige und zum Gold-Forward-Portfolio: z.B. separate Risikogates, Datenluecken, Nachrichtenfilter oder Kontoregeln.
- Kein Echtgeld, keine Order-APIs, keine Telegram-Nachrichten. **Selbst eine gute Rueckrechnung ist kein Nachweis künftiger Gewinne.**
- **Noch keine historischen Gold/BTC-OHLC-Dateien eingelesen und keine realen Ergebnisse gerechnet.** Die zuletzt im Chat gezeigten 500-Kerzen-Werte sind nur ein grober Kursbewegungsvergleich, kein Profitabilitaetsnachweis.
