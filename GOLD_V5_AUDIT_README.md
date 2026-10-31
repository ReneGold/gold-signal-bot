# Gold V5 – Forward-Prüfung (Punkte 2 und 3)

Unabhängige, **nur lesende** Auswertung. Die Handelsstrategie, Signalerzeugung, Telegram-Benachrichtigungen und Risiko-Gates bleiben unverändert.

## Punkt 2: Datenqualität und Forward-Auswertung
- Nur echte `FORWARD`-Trades mit `status=CLOSED`; Backfill und offene Trades ausgeschlossen.
- Trade-ID-Duplikate und ungültige R-Werte werden gemeldet.
- Erwartungswert (R/Trade), Gewinnquote, Profit Factor, geschlossener Drawdown und Verlustserie.
- Fehlende Indikator-Snapshots sichtbar; Aufteilung nach `regime`, sofern Daten vorhanden.
- Unter 30 abgeschlossenen Forward-Trades: Stichprobenwarnung. Das ist **keine** Live-Freigabe.

## Punkt 3: Kosten-/Stresstest
- Dieselben echten abgeschlossenen Trades werden zusätzlich mit **hypothetischen Mehrkosten** von 0,10 R, 0,25 R und 0,50 R je Trade geprüft.
- Kostenwerte sind **keine** behaupteten Brokerspreads. In der Praxis an Broker-Execution-Daten anpassen.
- Verlustserien und Drawdown werden separat ausgegeben. Kein Echtgeldhandel oder Auftragsversand.

## Anwendung
```bash
python3 -m unittest test_gold_v5_forward_audit.py
python3 gold_v5_forward_audit.py --output gold_v5_forward_audit.json
```
Standardmäßig liest das Tool `gold_v5_forward_ledger.csv`. Es erkennt `CLOSED_PAPER` sowie `CLOSED` und verwendet `signal_utc` zur Duplikatprüfung, `exit_utc` für die zeitliche Sortierung sowie `phase` für die Marktaufteilung. Die Pflichtspalten sind `cohort,status,net_R`. Beispielstruktur:

```csv
cohort,status,net_R,trade_id,signal_time_utc,regime
```

**Wichtig:** Eine nur aggregierte JSON-Zusammenfassung reicht nicht, um eine Verlustserie oder Kostenwirkung korrekt pro Trade zu rekonstruieren. Die Auswertung braucht den **tatsächlichen** vollständigen Forward-Trade-Export. Beispieldaten nicht als echte Ergebnisse einsetzen. Der bisherige Forward-Paper-Prozess wird nicht automatisch geändert.
