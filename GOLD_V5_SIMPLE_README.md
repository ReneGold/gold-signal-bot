# Gold V5 SIMPLE – kontrollierte Forschungsversion

**Status 2026-11-08:** Isolierter Prototyp. **Nicht produktiv, nicht live, keine Telegram-/Broker-Anbindung.** Bestehende Gold V5 Forward Paper Beobachtung sowie Bitcoin bleiben unverändert.

## Genau eine Signalstrategie
- XAU/USD, abgeschlossene 15m-Kerzen; übergeordnete 1h-Kerzen ebenfalls nachweislich abgeschlossen.
- LONG nur bei aufsteigendem EMA20 über EMA50 in **beiden** Zeitrahmen, SHORT umgekehrt.
- Vorherige 15m-Kerze berührt EMA20, aktuelle abgeschlossene 15m-Kerze bestätigt mit Schlusskurs über vorherigem Hoch (LONG) bzw. unter vorherigem Tief (SHORT) und passender Kerzenfarbe.
- Stop-Distanz als **Forschungsreferenz**: 1,5 * ATR14 im 15m-Chart; Ziel 2R. **Kein behaupteter, handelbarer Einstiegskurs** vor nächstem Kerzen-Open / Brokerquote.
- Kein V3.9-Score, Fibonacci, FVG, ADX oder pauschale H1-Seitwärtsmarkt-Sperre.

## Risikobudget
`risk_budget(equity_eur, daily_loss_eur, consecutive_losses, open_positions)` liefert nur den maximal zulässigen Verlust in EUR.
- 0,5 % Konto pro Trade; max. 1 % realisierter Tagesverlust; Pause nach zwei Verlusten; höchstens eine offene Position.
- **Keine automatische Lotgröße** bis Broker-Kontraktwert, Konto-/XAUUSD-Währung, Spread, Slippage und Stop-Order-Ausführung belastbar bestimmt sind.

## Test / Nachweis
- Code: `gold_v5_simple_signal.py`
- Offline-Tests: `python -m unittest -v test_gold_v5_simple_signal.py`
- Sicherheitsregeln schließen veraltete/unvollständige Kerzen und nicht fertiggestellte H1-Kerzen aus. Historische Gold-Handelspausen sind erlaubt; eine Lücke zwischen den zwei jüngsten Kerzen blockiert das Setup.
- **Tests noch nicht in GitHub Actions ausgeführt**, keine vollständigen historischen OHLC-Daten für seriösen Backtest vorhanden, noch keine beobachteten Forward-Trades dieser Variante.
- Vor produktivem Einsatz müssen Datenvollständigkeit, Session-Kalender, korrekte EMA/ATR-Initialisierung, Brokerkosten, Ausführungslogik und Fail-Closed-Betrieb geprüft werden.

## Freigaberegel
Keine Zusammenführung in den aktiven Forward-Bot und keine Telegram-Handelsmeldung, bevor (1) Offline-Tests bestanden, (2) unabhängiger historischer Backtest mit realen Daten und Kosten nachvollziehbar, (3) Live-Paper-Läufe ausreichend protokolliert und (4) Zustell- und Ausfallverhalten belegt sind.
