# Gold V5 – Prüfpunkte 2 und 3: Trade-Vergleich und unabhängige Kostenvalidierung

**Stand:** 2026-10-31 (UTC-Datenstand 12:50)
**Branch:** `gold-bot-v3-9-5-test`
**Status:** FORWARD PAPER ONLY — **KEINE FREIGABE FÜR ECHTGELD**

## Nachweisbarer Ausgangsstand
Quellen: `gold_v5_forward_summary.json` und `gold_v5_forward_performance.json`, jeweils Stand 2026-10-31 12:50 UTC.

- FORWARD-Signale: 1, geschlossen: 1, offen: 0.
- Gewinne: 1; Verluste/Break-even: 0; Netto-Ergebnis: +1.90306 R.
- INITIAL_BACKFILL: 5 (aus der FORWARD-Bewertung explizit ausgeschlossen).
- Gewinnquote 100 % bei n=1 **ist statistisch nicht aussagefähig**. Profit Factor mangels Verlusttrade nicht bestimmbar.
- Paper-Einstieg zum indikativen nächsten Kerzen-Open; keine tatsächlich ausführbaren Bid/Ask-Kurse.
- Die vorhandenen Daten weisen weder reale Spreads und Slippage noch Broker-Ausführung oder alle Gebühren nach.

## Punkt 2 – Gewinne und Verluste vergleichen

**Noch nicht möglich:** Es liegt bisher kein abgeschlossener Verlusttrade vor.

Für **jeden** künftigen FORWARD-Trade ist ein einheitlicher, nachvollziehbarer Datensatz zu erfassen:
- Signal-ID, Signal-Zeitpunkt UTC, Marktdatenquelle, Symbol, Intervall und FORWARD-Kohorte.
- Long/Short, Marktphase (Trend/Range), Entry-Grund, EMA20/EMA50, ATR und Volatilitätszustand.
- Geplanter Einstieg, Stop, TP, Risikoabstand, geplantes CRV.
- Geplanter gegenüber simuliertem Ausführungskurs; Spread, Slippage, Gebühren, ggf. Swap.
- Realisierter Exit-Grund (SL/TP/Timeout/anderes), Brutto-R, Kosten-R, Netto-R.
- News-Abstand/News-Risiko, Datenlücken und Filter-/Gate-Entscheidungen.

Auswertung getrennt für Gewinner, Verlierer und Break-even:
- Stichprobenanzahl pro Gruppe (stets mitberichten), Median/Verteilung von ATR, EMA-Abstand, Marktphase, Long/Short.
- Durchschnittlicher Nettogewinn und Nettoverlust in R, Erwartungswert, Profit Factor (falls definierbar), Drawdown.
- Vergleich verschiedener Konfigurationen **nur** auf gleicher Zeitbasis und mit gleichen Kostenvorgaben.
- Keine Parameteranpassung anhand einzelner Trades; keine rückwirkende Umklassifizierung von BACKFILL als FORWARD.

## Punkt 3 – Unabhängige Überprüfung und realistische Ausführung

**Status:** noch nicht abgeschlossen; bestehende Paper-Ergebnisse sind keine Broker-Ausführungsnachweise.

Prüfprotokoll:
1. **Unabhängige Datenquelle:** Signale/Zeiten gegen zweite Quelle für Spot-XAUUSD und Broker-Sessions abgleichen. CME-Zeiten nicht unbesehen auf Spot-XAUUSD übertragen.
2. **Bid/Ask und Spread:** Broker-spezifische historische Bid/Ask-Spreads je Signalzeit nachweisen; nicht pauschal Null ansetzen.
3. **Slippage:** konservative und Stress-Szenarien für den Einstieg/Ausstieg prüfen; besonders Stop-Ausführung und News-Spitzen.
4. **Kommission, Finanzierung, Kontraktgröße:** gemäß konkreten Broker- und Kontobedingungen erfassen, inklusive Pip-/Punktwert und Währungskonversion.
5. **Kostenbereinigter Replay:** Trade für Trade nach denselben Regeln, inklusive Reihenfolge bei SL/TP-Treffern in einer Kerze und Gaps, nachvollziehbar neu berechnen.
6. **Out-of-sample / Walk-forward:** eingefrorene Regeln, zeitlich getrennte Prüfperiode, kein Lookahead, keine rückwirkende Optimierung.
7. **Robustheit:** Sensitivität von Netto-R gegen höhere Spreads, Verzögerung und schlechtere Fills; fehlende Daten als fehlend markieren.
8. **Reproduzierbarkeit:** Commit-SHA, Datenversion, Parameter und Prüfergebnis je Bericht dokumentieren.

### Freigabe-Grenzen
- Solange reale/ausführbare Spreads, Slippage und Gebühren unbekannt bleiben, dürfen Ergebnisse **nicht als netto oder brokerrealistisch** ausgegeben werden.
- Der aktuelle Risikogate-Wert ALLOW ist eine technische Entscheidung und **keine Echtgeld-Freigabe**.
- Echtgeldentscheidung erst nach ausreichend umfangreicher unabhängiger FORWARD-Stichprobe, Kostenprüfung, Drawdown-Bewertung und Broker-Demotests.

### Nächster konkreter Arbeitsschritt
Vorhandene Forward-Trade-Logs auf die obigen Felder prüfen und ein separates Netto-R-Protokoll mit transparenten, nicht als real ausgegebenen Kosten-Szenarien aufbauen. Unbekannte Brokerparameter als `UNVERIFIED` markieren. Die bestehende Strategie und Live-/Telegram-Signale dabei unverändert lassen.
