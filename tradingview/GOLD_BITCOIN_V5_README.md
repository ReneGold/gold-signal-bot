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
