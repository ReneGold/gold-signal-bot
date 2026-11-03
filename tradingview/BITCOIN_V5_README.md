# Bitcoin V5 – Paper Signal (TradingView)

- Bitcoin-Adaption des **Gold-V5-Chart-Vergleichs** auf BTCUSD/BTCUSDT, 15-Minuten-Chart.
- Der bestehende **Gold V5** und deine bisherigen **Bitcoin V4.0**-Indikatoren bleiben unverändert.
- EMA20/EMA50, bestätigte Pullback-Breakouts, 1h-Marktphase mit EMA20/EMA50-Abstand < 0,5 ATR, Indikator-Tabelle mit Blockierungsgrund.
- Anders als bei Gold wird **keine Chicago-Handelspause** angewendet: BTC meist 24/7 (Datenfeed kann abweichen).
- Das ist ein **neuer Chart-Indikator**, noch KEIN vollautomatischer Bitcoin-V5-Python-Bot und noch KEINE Telegram-BTC-Signalstrecke.
- Historische Labels sind nur Kandidaten, nicht erfolgreiche oder tatsächlich beobachtete Echtzeit-Trades. Keine Broker-Orders.
- Indicative SL/TP-Marker werden vom Schlusskurs der Signalkerze aus gerechnet; reale/exakte Folgebalken-Entry-Fills oder Spreads werden nicht nachgestellt.
- Keine Score-65-Berechnung: Wir übernehmen die feste Gold-V5-Logik für einen fairen Vergleich. **Nicht für BTC validiert**; die 1h-Schwachmarktregel kann in starken Bitcoin-Trends viele Kandidaten ausschließen.
- Exchange-Daten, Marktsymbol, Zeitzonen und Lookback können von künftiger Serverlogik abweichen.
- Script muss in TradingView kompiliert und gegen Chart-Historie geprüft werden. Im Basic-Tarif kann die Anzahl eigener gespeicherter Skripte begrenzt sein. Code bleibt auf GitHub erhalten.

## Einfügen
1. TradingView -> BTCUSD oder BTCUSDT, 15m.
2. Pine Editor -> Neu erstellen -> Indikator (keine bestehende Version überschreiben).
3. Gesamten Inhalt von `bitcoin_v5_paper_signal.pine` einfügen, zum Chart hinzufügen und wenn möglich speichern.
