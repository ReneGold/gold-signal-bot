# PbD Original-Regelprotokoll Nr. 2 – Live-Session (DAX-Future)

**Quelle:** vollständiges vom Nutzer bereitgestelltes Transkript *Live-Session/PbD im DAX-Future*, ca. 19:38 min. **Erfasst:** 2026-11-24. Transkriptfehler möglich; zur endgültigen Originaltreue müssen Chart und Orderbuchbilder gegen die Zeitmarken abgeglichen werden.

## Wichtigster neuer Befund
**P bedeutet NICHT automatisch LONG.** Die im Video besprochene P-/Balance-Formation wird bei Rückkehr in bzw. Bruch unter die Balance auch für einen SHORT genutzt. Die Preisreaktion und Liquiditätsakzeptanz sind entscheidend. Das einfache Schema „P=Long, b=Short, D=Range“ aus Video 1 ist keine automatische Entry-Regel.

## Originalaussagen (Zeitmarken des Transkripts)

| Zeit | Nachvollziehbare Original-Aussage | Für Bot noch offen |
|---|---|---|
| 00:17–00:49 | Setup-Vorplanung mit PbD, konkrete Trade-Locations, Stop-Loss, Orderbuch und Footprint-Chart. | Genaue Gewichtung und Messgrößen nicht definiert. |
| 01:01–01:28 | Preopen, P-Struktur, bei Preisbewegung unter markierte Marke (112; ohne vollen Kontraktpreis) Short-Idee in Richtung Asien-Tiefs. | Exakte Formation/Marke/Entry-Typ nur im Chart sichtbar. |
| 02:24–03:56 | Weekly Market Profile, Single Prints, VPOC/Volumenknoten (Transkript „VPUR“), vorheriges Cash-Profil und Volumenbereiche für Schwäche- und Zielzonen. | Primär Future-Volumen nötig; Preisniveau-Zonen fehlen im Text. |
| 04:11–04:28 | Erster Stop liegt bei Short **über der relevanten Struktur**; kurzfristiger Spike hat sie nicht verletzt. | Abstand, Orderart und exakter Auslöser nicht genannt. |
| 05:23–05:46 | Bei ca. 1:2 CRV Teilgewinn möglich, sofern Teilposition existiert; konkrete Entscheidung situationsabhängig. | Kein verbindliches TP1 oder fixes 2R-Ziel für alle Trades. |
| 05:52–06:16 | Nach P-Erweiterung Markt **unter Balance**; weitere tiefere Kurse erst bei dortiger Akzeptanz plausibel. | Formale Bestätigung von Akzeptanz fehlt. |
| 06:21–06:56 | Footprint zeigt, wo gehandelte Liquidität tatsächlich liegt, im Unterschied zum kurzen Selloff mit wenig Umsatz; Teilgewinn wäre möglich gewesen. | Tick- und Volumendaten und quantitative Schwellen fehlen. |
| 06:56–07:26 | Bei drohendem **Wiedereintritt in die Range** Verlust von Buchgewinn vermeiden; Stop über **Oberkante der Seitwärtsphase**, ausdrücklich nicht pauschal auf Break-even. | Welche Zeitachse/Range-Kante? Stop-Timing und Buffer nicht spezifiziert. |
| 08:57–09:24 | Preopen dünne Liquidität und erhöhtes Spike-Risiko; nahe am Ziel vor Cash-Open kann Gewinnmitnahme sinnvoll sein. | Keine pauschale fixe Handelssperre oder Minutenzahl genannt. |
| 10:05–11:42 | Orderbuch-Geschwindigkeit, Verkäufer-/Käuferaggression und Absorption an Preiszonen als Fortsetzungs-/Abbruchhinweise. | Ohne Futures-Level-2/Footprint kein belegbarer Original-Trigger. |
| 10:46–10:54 | Konkretes Beispiel mit vorherigem Risiko von 23 Ticks und Bewegung 62 DAX-Punkten, als fast 3R beschrieben. | Ein Beispiel, **keine allgemeine Soll-Stopgröße**. |
| 13:00–13:48 | Euwax-Sentiment nur als zusätzliche konträre Einschätzung im damaligen Index-Kontext. | Keine generelle Gold-Regel. |
| 14:05–15:51 | Bei erwarteter Erschöpfung / Rücklaufgefahr Gewinn nehmen oder Stop über technische Liquiditäts-/Preiszone nachziehen; im Beispiel 74 Ticks Sicherung. | Kein allgemeiner Trailingalgorithmus. |
| 16:08–17:25 | Technisches Fazit: Aufwärtsmove → Balance → Liquiditätsarmut → **Wiedereintritt in Range** → wahrscheinlicher Abwärtsmove; Stop über **letztem Liquiditäts-/Balancebereich**. | Exakte Range-Konstruktion und Momentum-Schwelle offen. |
| 18:58–19:38 | Ziel an zuvor identifizierter großer Liquiditätszone erreicht; dort erwartete Reaktion; kein automatisch gegenläufiger Long, wenn Gesamtstruktur zu schwach. | Kein formaler Zielalgorithmus / Contra-Entry. |

## Was sich gegenüber Video 1 konkretisiert hat
1. Marktprofil und Liquiditätszonen kommen zusätzlich zu den Preiskörpern hinzu.
2. Wiedereintritt in Balance/Range kann gegen vorherige Impulsrichtung gespielt werden – **keine 1:1-Zuordnung Formation → Orderrichtung**.
3. Initialer und späterer Stop werden **strukturell über relevanten Zonen** statt anhand beliebiger ATR-Multiplikatoren gesetzt.
4. Teilgewinn bei circa 2R **optionale Beispielentscheidung**, kein allgemeines fixes TP-Modell.
5. Orderbuch/Footprint ist integraler Bestandteil der Live-Entscheidung; ein Gold-Spot-OHLC-Backtest allein reproduziert das Originalsystem nicht.

## Noch zwingend offene Originalregeln
- Wie genau P/b/D und Balance-Grenzen aus O/C-Kerzen und ggf. Markt-/Volumenprofil erzeugt werden.
- Welche objektive Bedingung einen gültigen Ausbruch, einen Wiedereintritt oder eine „Akzeptanz“ bestätigt.
- Wie viele Tests/Rejections für Entry erforderlich sind; präzise Orderart und Zeitregel.
- Welche originalen Bid-/Ask-/Volumen-/Delta-/Footprint-Schwellen gelten und ob sie definierbar sind.
- Exakte Definition von Stopzone und Buffer sowie Trailing-/Teilverkaufsvorschrift.
- Klärung, wie **DAX-Futures**-Daten/Regeln legitim auf **Gold XAUUSD Spot** übertragen werden können (Spot hat kein zentrales Orderbuch). Eventuell Gold-Futures (COMEX GC) als separate Quelle, nach expliziter Abstimmung.
- Verifizierte Brokerkosten, Slippage, Tick-Werte, Handelszeit und unabhängig testbare Daten.

## Forschungsentscheidung
Die Originalmethode ist mit den beiden Transkripten **noch nicht vollständig automatisierbar**. Bis die Chartbilder und objektiven Regeln vorliegen, nur quellengebundene Spezifikation – keine Trading-Signale, kein Backtest als „Original PbD“ und keine Echtgeldfreigabe.

**Nächster belegbarer Arbeitsschritt:** Screenshots des Videos bei ca. 01:08, 04:20, 06:06, 07:18, 10:22 und 16:25 sowie weitere Lehrinhalte mit explizit benannten Entry-/Exit-Regeln.
