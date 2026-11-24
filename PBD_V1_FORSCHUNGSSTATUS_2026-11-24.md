# Gold PbD-inspirierte Hypothese V1 – Laufstatus, 2026-11-24

**Branch:** `gold-pbd-hypothesis-v1`. Der bestehende V5-Produktions-/Paper-Zweig wurde nicht bearbeitet.

## Geprüfter technischer Lauf
- GitHub Actions: https://github.com/ReneGold/gold-signal-bot/actions/runs/45335710090
- **Alle 7 Offline-Sicherheitstests bestanden:** Syntax, Ausbruchs-/Balanceerkennung, Vermeidung von Lookahead, Kerzenlücken, Stop zuerst bei unklarer Reihenfolge und leere Statistiken.
- **Historische Trade-Statistik liegt NICHT vor.**
- Verifizierter Blocker: Datenanbieter Dukascopy verweigerte historischen API-Export am 24.11.2026 mit HTTP 403 beim Aufruf für 01.08.2026. Workflow beendete den Daten-Download; Import und Backtest wurden zurecht übersprungen.
- 403 ist ein verweigerter Datenabruf; Retry/Umgehung ohne legitime Datenquelle wäre keine verlässliche Strategieauswertung.
- Die Dukascopy-Bibliothek dokumentiert entsprechende 403-Probleme; auch ein öffentliches GitHub-Issue beschreibt die Unterbrechung: https://github.com/Leo4815162342/dukascopy-node/issues/264.

## Vorab fixierte eigens definierte Hypothese
- Nur XAUUSD 15-Minutenkurskerzen (indikative BID-Historie).
- Nach vier aufwärts gerichteten Impulskerzen (Impuls >= 2x mittlere Hoch-Tief-Spanne der vorherigen 20 Kerzen) vier begrenzt schwankende Balancekerzen, dann bearisher Schlusskurs unter Minimum der Körperzone: mögliche SHORT-Situation.
- Entry erst nach abgeschlossener Signalkerze (nächster Kerzen-Open), Stop über Body-Zone plus 0.2 Referenzspanne, TP 2R, maximal 16 Kerzen Haltezeit.
- Hypothetische Kosten: 0.80 USD/oz Roundtrip, **kein** verifizierter ausführbarer Broker-Spread.
- Das ist eine *eigene* simplifizierte Preis-Aktions-Hypothese, **keine vollständig originale PbD-/Footprint-Methodik**.

## Verbindliche Datenanforderungen vor einem Resultat
1. Historische XAUUSD 15-Minuten-OHLC mit dokumentierter Quelle, UTC und unvermischter Bid-/Ask-Konvention bereitstellen.
2. Quelle und Preisformat plausibilisieren; prüfen, ob Wochenende und Session-Lücken plausibel sind. Keine erfundenen Kerzen / kein Forward Fill.
3. Dieselbe eingefrorene Hypothese **ohne Parametertuning** auf den Daten rechnen.
4. Resultat mit Zeitraum, Tradeanzahl, Netto-R, Profitfaktor, DD und Datenfehlern berichten.
5. Unabhängigen späteren Zeitraum und verifizierte Spreads/Slippage nachweisen, bevor überhaupt ein Paper-Start diskutiert wird.

**Bewertung derzeit:** ENGINE TESTS GREEN / MARKET DATA BLOCKED / PERFORMANCE UNKNOWN / NO LIVE RELEASE.
