# Gold Research V1 — neue, isolierte Forschungslinie

**Status:** Neue Strategie als Forschungsprototyp implementiert; kein profitabler Edge nachgewiesen. **Keine Orders, keine Telegram-Nachrichten, kein laufender Scheduler, keine Änderung der bestehenden V5.**

## Warum ein Neuanfang?
Gold V5 SIMPLE verlor im ersten historischen Pilot (August 2026) bei 46 Abschlüssen **-3,1658 R** (Modellkosten, nicht verifizierte Broker-Fills). Dieser Zeitraum, das OHLC-Datenmodell und die bestehende Strategie reichen nicht als Nachweis künftiger Gewinne. V5 bleibt unangetastete, historische Referenz; neue Forschung ist explizit getrennt.

## Eine neue Hypothese
**XAUUSD Trend-Breakout statt EMA-Rücksetzer.** Auf einer vollständig geschlossenen 15m-Kerze:
1. Nur die **letzte vollständig geschlossene 1h-Kerze** darf die Richtung vorgeben (EMA20 > EMA50 plus steigender EMA20 für LONG; umgekehrt SHORT).
2. LONG: bestätigter Schluss **über dem höchsten Hoch der 20 vorausgehenden 15m-Kerzen**, bullische Schlusskerze; SHORT entsprechend unter 20-Tief und bearische Kerze.
3. ATR14-basierte indikative Stop-Distanz von 1,5 ATR und vorläufiges Untersuchungsziel 2R.
4. Maximal 0,5% Euro-Risikobudget pro Trade, 1% tägliche Verlustgrenze, Pause bei 2 Verlusten, nur 1 Position. Ohne geprüfte Brokerkontraktdaten **keine Lotgröße**.

Keine Fibonacci-/FVG-/ADX-/Score-Kombination, keine willkürliche Optimierung von 20/50/14/2R nach Monatsgewinn.

## Strikte Mess- und Freigaberegeln
- Vor jedem Backtest: Gold-Daten von mindestens 12 Monaten, konsistente XAUUSD 15m/H1-Quelle, Session-Gaps, UTC und plausibles Volumen/Preismodell; jede 1h-Kerze erst nach ihrem Schluss verwenden.
- Daten in Entwicklungs- und vorher unangetastete Testintervalle aufteilen. Referenz: bisherige V5 SIMPLE **nur nach Verifikation der Daten und identischer Kosten-Methodik**.
- Ausführung und Kosten: Einstieg erst am nächsten Kerzen-Open, pessimistische Same-Bar-SL-Regel, Spread/Slippage und Outages; Brokerpreisquelle/Bid-Ask nachprüfen.
- Vorab Kennzahlen festlegen: Anzahl Trades, durchschnittliches Netto-R, Gesamt-Netto-R, Profitfaktor, maximaler Drawdown, monatliche Stabilität, Qualitätsprobleme.
- Nur falls unabhängiger Test nach Kosten ausreichend positiv **und** Paper-Forward-Test zuverlässig, kann eine getrennte Signal-/Telegram-Version erwogen werden; kein garantiertes Einkommen.
- Negative/unklare Resultate = Hypothese ablehnen, **nicht** nachträglich Parameter auf diesen Testmonat optimieren.

## Dateien
- `gold_research_v1.py` — reine Signalhypothese und Euro-Risikobudget; kein Netzwerk.
- `test_gold_research_v1.py` — synthetische Tests für Zukunftswissen, Datenlücken, bestätigte Kerzen und Risikogrenzen.
- `.github/workflows/gold-research-v1-tests.yml` — GitHub-Actions-Syntax- und Unit-Test (ohne Marktdatenanbieter).

**Der Code ist erstellt; die CI-Ausführung und die Performance sind separat nachzuweisen.** Dieser V1-Prototyp ist nicht vollständig marktfertig: Handelskalender, Echtzeit-Datenversorgung, Indikator-Warmup sowie Ausstiegs-/Performance-Simulation sind noch auszuarbeiten.
