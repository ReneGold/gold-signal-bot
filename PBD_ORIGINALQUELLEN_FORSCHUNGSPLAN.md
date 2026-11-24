# PbD nach Tom Vorwald — quellengebundene Forschung (XAUUSD)

**Status (2026-11-24):** Quellenprüfung, **KEIN** programmierbares Original-Regelwerk, **KEINE** Trades.
**Branch:** gold-pbd-source-research. V5 auf main bleibt unverändert.

## Primärquellen (öffentlich)
1. Tom Vorwald, *The Easiest Day Trading Strategy for Beginners (PBD Method)*, veröffentlicht 2026-07-03:
   https://www.youtube.com/watch?v=Q3ya0x2mKcU
   Die öffentlich zugängliche Videobeschreibung nennt:
   - Marktphasen Gleichgewicht / Ungleichgewicht (70/30 als Aussage des Urhebers, keine verifizierte Marktstatistik)
   - P-Profil als Aufwärtstrendfortsetzung, b-Profil als Spiegelbild für Short, D-Profil als Balance und Gegentrendhandel
   - Bedeutung von Eröffnungs- und Schlusskursen gegenüber reinen Hoch-/Tief-Extremen
   - Unterscheidung zwischen echtem Trendfortsetzen und Wiedereintritt in Balance/Preiszone
   Die Beschreibung ist **keine** vollständige operationalisierte Ein-/Ausstiegsregel. Zeitmarken des Videos: 06:00 P, 08:30 Retest, 10:30 b, 12:30 D.
2. TradeTheTraders, Mentor-Profil Tom Vorwald:
   https://tradethetraders.com/tom-vorwald
   Bestätigt die Zuordnung der PbD-Methode zum Entwickler.
3. TradeTheTraders, Mentor-Profil Patrick Nill:
   https://tradethetraders.com/patrick-nill
   Nennt P-, b- und D-Formationen als Breakout- und Balance-Phasen.
4. TradeTheTraders, Mentoring:
   https://tradethetraders.com/trading-mentoring
   Hinweis: vorwiegend Futures-Schwerpunkt; Umsetzung auf Spot XAUUSD erfordert eigene Prüfung.

## Gegenüberstellung: belegt vs. ungeklärt
| Thema | Dokumentationsstand |
|---|---|
| Die drei Formationsbezeichnungen P/b/D | Belegt |
| P und b: trendgerichtet; D: Balance/Gegentrend | Belegt |
| Relevanz von Eröffnungs- und Schlusskursen | Belegt |
| Formations-Schwelle: exakte Kerzenanzahl, Zeitfenster, Volumenprofil/Preiszone | **OFFEN** |
| Originale Bedingungen für ein gültiges P, b und D | **OFFEN** |
| Exakter Entry-Trigger und Retest-Bedingung | **OFFEN** |
| Originaler Stop-Loss, Take-Profit, Time-Exit | **OFFEN** |
| Gold-spezifische Handelszeiten und Brokerdaten | **OFFEN** |
| Aussage zur historisch belastbaren Profitabilität auf XAUUSD | **NICHT BELEGT** |

## Forschungs-Gates
1. **Quellen-Gate:** Vollständige autorisierte Originalregeln aus Vorwalds Video/Schulungsunterlagen erfassen, mit Zeitmarke/Seite; Unklarheiten explizit als solche dokumentieren.
2. **Definitions-Gate:** Jede Regel deterministisch und ohne Zukunftsdaten formulierbar; Interpretation als Abweichung kennzeichnen, nicht als Originalregel ausgeben.
3. **Daten-Gate:** XAUUSD Tick/Bid-Ask, relevante Marktzeiten, Spread, Slippage und Session-Gaps prüfen. Futures-Volumenprofile sind nicht automatisch durch Spot-OHLC ersetzbar.
4. **Backtest-Gate:** Erst feste Regeln, dann Historie mit Kosten, Gap-Audit und separatem Out-of-Sample; keine Parameter-Suche auf dem Testzeitraum.
5. **Paper-Gate:** Nur bei positivem robustem Ergebnis; genügend real beobachtete Signale und zuverlässiger Scheduler.
6. **Echtgeld-Gate:** Keine Freigabe ohne unabhängige Evidenz und Broker-Ausführungstest.

### Wichtig
Es wäre irreführend, aus den bloßen Namen P/b/D sofort eine Handelsstrategie mit z. B. EMA-Filtern, frei erfundenem SL=1.5 ATR oder 2R-TP als „original PbD“ zu programmieren. Noch kein Bot-Code und keine Orders.
