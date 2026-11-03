# Gold V5 – TradingView-Anzeige (Paper-Vergleich)

- Datei: `gold_v5_paper_signal.pine`, Pine Script Version 6.
- Für den XAUUSD-Chart mit **15 Minuten**. In TradingView: Pine Editor öffnen -> neues Indikator-Skript -> Code vollständig einsetzen -> speichern -> „Zum Chart hinzufügen“.
- Bestehende Gold V4.0 und Bitcoin V4.0 **nicht überschreiben**.
- Zeigt EMA20/EMA50, LONG/SHORT-*Kandidaten* auf abgeschlossenen Kerzen und eine Tabelle der aktuellen Bedingungen.
- Entspricht der Grundlogik der **eingefrorenen** Gold-V5-Strategie (1H-Schwachmarkt < 0,5 ATR, EMA20/EMA50, Rücksetzer an EMA20, Kerzen-Breakout, Chicago-Referenzsession).
- Ist **nicht 1:1** die Python-Ausführung: 1H-Daten werden konservativ mit dem letzten vollständig bestätigten H1-Wert betrachtet; Broker-Datenquellen und Zeitpunkte können abweichen; Portfolio-Risikogrenze, offene Paper-Position, frischer Live-Run, Duplikatschutz und tatsächliche Nächste-Kerze-Fills lassen sich im Indikator nicht synchronisieren.
- Gezeichnete SL/TP-Werte sind nur Abstände auf Basis des **Schlusskurses** und ATR; Python setzt den tatsächlichen Paper-Entry zum folgenden Open und legt die Levels ab diesem Entry fest.
- **Kein Score 65, keine Orders, keine TradingView-Alerts.** Signale im Chart sind retrospektive Muster, **keine** bestätigten neuen Live-/Forward-Trades.
- Nicht als profitable Strategie geprüft. Die Pine-Quelle muss in TradingView kompiliert und die visuellen Ergebnisse mit identischem Marktdatenanbieter gegen Python geprüft werden.
