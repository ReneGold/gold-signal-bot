# PbD: Original-Regelprotokoll Nr. 1 – Tom Vorwald

**Quelle:** vom Nutzer bereitgestelltes deutschsprachiges Transkript des Videos *Die einfachste Trading-Strategie überhaupt / PbD-Methode*, rund 17:36 Minuten.  
**Ausgewertet:** 2026-11-24.  
**Status:** Echte Aussagen aus dem Transkript mit Zeitmarken; **keine vollständige regelbasierte Handelsstrategie**. Das Transkript enthält automatisch erzeugte Schreibfehler, daher Zeitangaben annähernd. Chartbilder liegen nicht vor.

## Originalaussagen und beobachtbare Handlungslogik

| Zeitmarke | Aussage / Logik im Video | Präzision für einen automatischen Bot |
|---|---|---|
| 02:05–02:20 | Zuerst Trend-/Ungleichgewichtsphasen von Seitwärts-/Gleichgewichtsphasen unterscheiden. | Keine numerische Definition der beiden Phasen. |
| 05:21–05:35 | Für die Einordnung **Eröffnungs- und Schlusskurse**, nicht absolute Hoch-/Tief-Extrema, verwenden. | Klarer methodischer Grundsatz, aber keine konkrete Berechnungsvorschrift. |
| 06:39–07:19 | **Erst dynamischen Impuls abwarten**, anschließend Seitwärtsphase finden; daraus entsteht das **P-Profil** im gezeigten Long-Beispiel. Impuls bedeutet möglichst ohne große Rückläufe. | Weder minimale Impulsstärke noch maximale Rückläufe noch Zahl der Seitwärtskerzen definiert. |
| 07:47–08:29 | Markt akzeptiert nach dem Aufwärtsimpuls höhere Preise; Seitwärtsphase nach oben schafft eine potenzielle Long-Fortsetzung. | 'Akzeptanz' und 'Liquidität' nicht quantitativ definiert. |
| 09:06–10:18 | Nach Seitwärtsphase wird ein **Ausbruch vorzugsweise per Schlusskurs** nach oben bewertet; **Rücklauf/Retest** an frühere Liquiditätszone kann Trendfortsetzung begründen. | Keine exakte Zone, Retest-Toleranz, Entry-Kerze, Invalidierungsregel oder Orderart. |
| 10:36–12:49 | Erst Dynamik, dann Schlusskurse, dann Range/Seitwärtsphase; nach Level-Akzeptanz mögliche Fortsetzung; bei spätem Test und **Ablehnung** kann Short-Fortsetzung entstehen (**b**-Logik). | Objektive Definition für 'Ablehnung', Short-Einstieg und exakte Range-Grenzen fehlt. Transkript beschreibt teils Long-Beispiele im Kapitel 'B'. |
| 13:15–13:42 | Impuls verschiebt Akzeptanz zu neuem Preisbereich, der später erneut getestet wird; P und b als Konzepte für stärkere Bewegungen. | Nur qualitative Richtungsaussage. |
| 13:50–15:27 | **D-Profil** = größere Seitwärts-/Balancezone, mehrfache Bewegungen zwischen Ober- und Untergrenze; im Bereich eher **oben Short / unten Long**, bis starker Ausbruch die Balance beendet. | Anzahl Berührungen, Grenzberechnung, Einstiegstrigger, Ausbruchsvalidierung und Risiko fehlen. |
| 16:41–17:11 | Scheitern P-/b-Trendfortsetzungen wiederholt und kehrt Preis in Bereich zurück, deutet das laut Sprecher auf größere Balancephase und mögliche D-Logik hin. | 'Wiederholt', Rückkehr und Wechseltrigger nicht numerisch bestimmt. |
| 17:11–17:27 | Sprecher behauptet circa 70% Seitwärtsphasen und vorteilhafte Treffer in dynamischen P-/b-Phasen. | Keine im Transkript nachprüfbare Statistik; **nicht** als belegte Performance verwenden. |

## Noch nicht bekannte Originalregeln – zwingend vor einer 'exakten' Implementation klären

1. **Zeiteinheiten:** Auf welchen Charts werden Impuls, Formation und Trigger gemessen? Braucht jede Formation einen gesonderten Zeitrahmen?
2. **P/b/D-Grenzen:** Durch welche konkret ausgewählten Kerzenkörper (O/C) entstehen obere/untere Grenze? Min./Max.-Dauer?
3. **Impuls:** Wie viele Kerzen, welche Mindestbewegung, welche maximalen Gegenbewegungen?
4. **Bestätigung:** Welcher Schlusskurs zählt als echter Breakout/Break-in? Ist ein weiterer Schlusskurs über der Zone nötig?
5. **Retest/Ablehnung:** Welches Kursereignis bestätigt Ablehnung, und wann genau Order?
6. **Invalidierung / SL:** Exakter ursprünglicher Stop, Regeln für Stopverschiebung.
7. **TP / Exit:** Feste Ziele, Positionsmanagement, Zeitstopp, Verlustserien?
8. **Setup-Filter:** Welches Volumen-/Orderflowmaterial, falls nötig, und welche Handelszeiten?
9. **Anwendbarkeit XAUUSD Spot:** Beispiele des Videos beziehen sich auf andere Märkte; tatsächliche ausführbare Brokerdaten und Marktsitzung separat prüfen.

## Konsequenz für Gold-Bot

- **Keine Strategie-Automatisierung** mit dem Etikett 'Original PbD' aus diesem ersten Video allein.
- Möglich: ein **rein beschreibendes, nicht handelndes** Werkzeug für Chartannotationen nach manuell bestätigten Zonen; keine eigenständigen Handelssignale.
- Nächste Quelle: Live-Trading-Video mit konkreten Entries, Stops, Exit und visuellem Chart; Transkript plus Screenshots zu den genannten Zeitmarken. 
- Jeder später nötige Schwellwert, den Tom nicht ausdrücklich vorgibt, ist **eigene Forschungsannahme**, nicht Originalregel.
