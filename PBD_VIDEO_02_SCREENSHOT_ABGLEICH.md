# PbD – Video 2: Abgleich mit sechs Nutzer-Screenshots

**Quelle:** Von Nutzer hochgeladene YouTube-Screenshots, 2026-11-24, zum Video `https://www.youtube.com/watch?v=ZZeET7ng1nk`. Gegenübergestellt mit dem vom Nutzer gelieferten Video-2-Transkript. **Keine** Übernahme der Bilder ins Repository, nur Beobachtungsprotokoll. Zeitpunkt ist die Videoposition, nicht die Aufnahmezeit.

## Sichtprüfung

| Videozeit | Sichtbar im Screenshot | Bestätigt im Transkript | Was NICHT sicher feststeht |
|---|---|---|---|
| 01:08 (2 Screenshots, praktisch gleiche Szene) | Multi-Chart mit Orderbuch/DOM und Volumenprofil; Chart links zeigt eine horizontale Referenzlinie, rechts volatile Kursstruktur. | P-/Preopen-Setup; unter einer als '112' abgekürzten Marke wird eine mögliche Short-Position angesprochen. | Exakte vollständige Preisangabe und die technisch programmierbare Entry-Bedingung sind aus dem Screenshot nicht zu gewinnen. |
| 04:20 | Vier Chart-/Orderbuchansichten mit erkennbarer Reaktion nach Rücklauf; Preopen-Kontext. | Vorwald erklärt, dass sein initialer Stop **über einer Struktur** liegt und ein Spike diese Struktur nicht herausgenommen hat. | Welcher Balken als absolute Strukturgrenze zählt, Stop-Buffer, exakte Zahl; Bildschirmfoto erlaubt keine zuverlässige Tick-Rekonstruktion. |
| 06:06 | Chart wird durch einen vergrößerten Screenshot überlagert: grüne Aufwärtsbewegungsannotation und kleine grüne/violette Balancezone nahe ihrem Ende; rote Markierung nach unten. | Markt sei nach Erweiterung eines P wieder unter der Balance; tiefere Preise nur bei weiterer Akzeptanz. | Rot/grün sind visuelle Hinweise, keine dokumentierten allgemeinen Stop/TP-Formeln. Vorherige Kursformation kann aus der Einzelaufnahme nicht formalisiert werden. |
| 07:18 | Markierte violette kleine Zone am jüngsten Hoch/Rücklauf im unteren linken Chart; Chart unten links zeigt anschließende Abwärtsbewegung. | Stop wird bei Short an Oberkante der Seitwärtsphase statt pauschal auf Entry nachgezogen. | Exakter Zonenalgorithmus, Stop-Offset und gültiger Stop-Update-Zeitpunkt bleiben offen. |
| 16:25 | Vergrößerte, visuell annotierte Chartansicht: türkisfarbener oberer Reaktionsbereich und grüne Balance-/Rücktrittszone; links weitere markierte Balance nahe jüngstem Hoch. | Sprecher begründet abwärtsgerichtete Idee mit **Wiedereintritt in die Range** nach Top/Balance und Liquiditätsarmut. | Eintrittsschwelle (Tick/Kerzenschluss/Volumenkriterium) lässt sich nicht aus dem Standbild feststellen; exakte Entrypreise/Fill nicht ablesbar. |

## Fachliche Schlussfolgerungen – Quelle vs. Interpretation
- **Durch Quelle gestützt:** Vorwald nutzt P/b/D-Kontext mit mehreren Charts, *lokalisierter Balance*, Futures-Orderbuch und Volumenprofil; orientiert seinen Short-Stop an einer **Struktur/Oberkante der Seitwärtszone**, statt ihn pauschal auf Break-even zu setzen.
- **Durch Quelle gestützt:** 'P' garantiert keinen LONG-Trade. Ein Wiedereintritt in eine Balance wird im gezeigten Beispiel zur Begründung des Short-Szenarios verwendet.
- **Interpretation, nicht Originalregel:** Die grünen, roten, violetten oder türkisfarbenen Rechtecke als universell programmierbare PbD-Zonen verwenden; visuelle Markierungen sind keine dokumentierte Formel.
- **Kritische Lücke:** Ein einzelner Chart-Screenshot liefert keine quantitative Beschreibung von Dynamik, Akzeptanz, Footprint-Delta, Volumenprofil-Level und Stoppuffern. So wäre ein automatisierter 'Original PbD'-Bot weiterhin nicht quellentreu.
- **Übertragung auf XAUUSD:** Screenshots zeigen DAX-Futures mit DOM/Volumenprofil; Spot-Gold-OHLC hat kein zentrales Orderbuch. GC-Futures würden andere Instrument-/Tick-/Session-/Kostenregeln erfordern.

## Nächste Forschungsentscheidung
Kein nachgestellter Entry-Algorithmus mit frei erfundenen Grenzwerten. Für vollständige Regeldefinition entweder Lehrmaterial mit expliziten quantitativen Bedingungen oder präzisierende Informationen vom Urheber über Formations-/Entry-/Exit-Regeln sowie erforderliche Orderflow-Daten. Nach Quellen-Gate zuerst reproduzierbare manuelle Annotation/Blind-Labeling von mehreren Beispielen, dann Hypothesentest und unabhängigen Backtest. Keine Echtgeldaktivierung.
