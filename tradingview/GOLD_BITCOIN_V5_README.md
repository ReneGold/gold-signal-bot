# Gold & Bitcoin V5 – ein gemeinsamer TradingView-Indikator

**Ziel:** EIN gespeichertes Pine Script fuer zwei getrennte Charts (Gold und BTC) statt zwei Skripte.

- Auf **XAUUSD** gelten die bisherigen Gold-V5-Chartregeln mit angenaeherter Chicago-Referenzpause.
- Auf **BTCUSD/BTCUSDT** gelten dieselben Kernmuster ohne Chicago-Pause (BTC meist 24/7).
- Andere Symbole werden nicht als Handelssignal bewertet.
- **Immer 15 Minuten** und vorzugsweise zwei getrennte Chartlayouts/Browser-Tabs desselben TradingView-Kontos.
- Kein Orderhandel, keine TradingView-Alerts, keine Telegram-Verbindung.
- Die bestehenden separaten Versionen und der Gold-Python-Bot bleiben unveraendert.
- Anders als Gold Python-V5 hat der Chartindikator keine Positionsverwaltung, keinen Daily-Risk-Gate, keine GitHub-Job-Frischepruefung oder Paper-Fills. Chart-Marker sind KEINE bestaetigten Forward-Trades.
- Pine-Code ist statisch auf Plausibilitaet kontrolliert, muss in TradingView selbst kompiliert und auf beiden Symbolen angezeigt werden. Die zeitlich exakte Uebereinstimmung mit Python ist noch NICHT nachgewiesen.
- Falls TradingView nur ein eigenes gespeichertes Skript erlaubt: vorhandenen Gold-V5-Code zuerst extern sichern (liegt auf GitHub), dann in dem vorhandenen, gespeicherten Gold-V5-Skript den Inhalt durch diesen gemeinsamen Code ersetzen und speichern. **Nicht** zusaetzliche Skripte erstellen; den bestehenden Namen ggf. spaeter in „Gold & Bitcoin V5 – Paper Signal“ umbenennen.
- Fuer zwei Tabs: dasselbe gespeicherte Skript auf beiden Charts laden, getrennte Layouts verwenden und das jeweilige Layout speichern. Anzeigen in zwei offenen Tabs sind moeglich, jedoch nicht gleichbedeutend mit lueckenloser Alarm-/Server-Ueberwachung.

## Vergleichstest
1. XAUUSD / 15m: Tabellenkopf zeigt GOLD; Gold-Handelspause gilt.
2. BTCUSD / 15m: Tabellenkopf zeigt BITCOIN; Sitzungszeile zeigt BTC 24/7.
3. Andere Ticker/Zeitrahmen: klare Warnung und keine V5-Marker.
4. Erst nach erfolgreichem TradingView-Compile und Chartvergleich als eingerichtet kennzeichnen.

## Erweiterung 2026-11-04: transparentes Score-Audit

Ein Zusatzbereich der Chart-Tabelle zeigt erstmals einen **V3.9-inspirierten** Informationsscore fuer LONG und SHORT und Einzelbefunde fuer Marktstruktur, BOS, Sweeps, einfache FVG-Pruefung, Fibonacci, Kerzenkoerper, Momentum, ADX und Volatilitaet.

**Achtung:** Das ist *keine* identische Portierung des historischen V3.9-Algorithmus. Insbesondere sind H1-Gewichtung, FVG-, Kerzenmuster- und Range-Regeln verkuerzt. Der Score ist **nicht kalibriert** und misst keine Gewinnchance. **Kein Mindestscore und kein hinzugefuegter Indikator beeinflusst die unveraenderten V5-Chart-Einstiegsmarker.**

Der Gold-Python-Forward-Bot verwendet weiterhin eigene feste Eintrittsregeln und sein Paper-Risikogate. Der Bitcoin-Chartindikator ist kein live ausfuehrender BTC-Python-Bot.

### Noch zu pruefen
- Pine-v6-Compile in TradingView auf beiden Symbolen. GitHub speichert Text, fuehrt aber keinen TradingView-Compiler aus.
- Vergleich historischer Kandidaten mit altem gemeinsamen V5 vor und nach der Aenderung: die V5-Signalbedingungen sind unveraendert; dies muss mit echten gleichen Chart-Daten verifiziert werden.
- Messung der beobachteten Forward-Ergebnisse je Scoregruppe erst bei ausreichender Stichprobe. Ein einziger abgeschlossener Gold-Forward-Trade reicht nicht.
