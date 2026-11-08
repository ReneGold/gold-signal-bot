# Gold V5 – Optimierung 01: 1H-Marktphasenfilter (nur Forschung)

Stand: 2026-11-08. Referenz: `gold-bot-v3-9-5-test`, Datei `gold_v5_decisions_observed.json`.
**Kein Eingriff in laufende Paper-Signale, Risiko-Gates, TradingView oder Telegram.**

## Fragestellung
Verhindert die bestehende Regel `abs(EMA20_1h - EMA50_1h) / ATR14_1h < 0.5` genügend vollständig bestätigte Setups, um eine **separat getestete** Trendmarktvariante zu rechtfertigen?

## Befund: tatsächlich live beobachtete abgeschlossene Kerzen
- 31 gespeicherte Entscheidungen (2026-11-03 bis 2026-11-08); keine vollständige Marktabdeckung.
- 16 Entscheidungen nennen `MARKET_PHASE_BLOCKED` unter allen Ablehnungsgründen (Mehrfachgründe möglich).
- **Nur eine** Entscheidung enthält ausschließlich `MARKET_PHASE_BLOCKED`: Signal-Schluss 2026-11-05 17:45 UTC, Richtung SHORT. EMA-Trend, EMA20-Kontakt, abgeschlossener Ausbruch, Session und Risikogate waren laut Snapshot erfüllt.
- Bei den übrigen 15 Entscheidungen mit Marktphasenblockade gab es **weitere** Sperrgründe. Den Phasenfilter allein abzuschalten hätte dort keinen V5-Kandidaten erzeugt.
- Aus dieser Diagnose lässt sich **kein hypothetischer Gewinn/Verlust** des abgelehnten SHORTs ableiten.

## Eine Hypothese – ein Vergleich
Die bestehende Range/Weak-Regel **nicht ersetzen**. Eine alternative, separat simulierte **Strong-H1-in-Richtung-des-15m-Trends**-Variante nur dann weiterverfolgen, wenn sie bei unveränderten Rücksetzer-/Bestätigungs-/Risiko-Regeln robust ist. Bestehendes read-only Werkzeug: `gold_v5_regime_backtest.py` mit echten 15m-/1h-OHLC-Daten desselben Feeds.

## Prüfplan
1. Historische Gold-Datensätze mit geprüften Zeitstempeln aufteilen: Entwicklung vs. **späterer, zuvor nicht verwendeter** Testzeitraum; keine erfundenen Kerzen oder rückdatierten Forward-Signale.
2. `frozen` gegen `strong` mit unveränderten 15m-Kriterien, 1.5 ATR Stop, 2R-Ziel und unveränderten Sessions vergleichen; Spread/Slippage als Sensitivität abbilden.
3. Pro Variante Trades, mittleres R, Drawdown, monatliche Stabilität und Datenlücken prüfen. Ein einzelner erfolgreicher Trade reicht nicht.
4. Nur bei belastbarem Out-of-Sample-Ergebnis **eine getrennte Paper-Variante** beobachten; erst danach eventuell Änderung an aktiver V5 erwägen.

## Entscheidung heute
**NO CHANGE** an produktiver Gold V5: zu wenige beobachtete vollständig bestätigte, ausschließlich von H1 blockierte Setups; vorhandenes Forward-Ledger enthält nur einen abgeschlossenen Trade. Telegram-Zustellung und GitHub-Takt sind getrennte Zuverlässigkeitsthemen, keine Filteroptimierung.
