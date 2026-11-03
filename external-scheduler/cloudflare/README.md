# Gold V5 – externer Taktgeber (Cloudflare Worker)

**Status: nur vorbereitet.** Diese Dateien deployen nichts automatisch. Cloudflare-Zugang und GitHub-Token müssen erst vom Repository-Inhaber eingerichtet werden.

## Architektur

Cloudflare-Cron (UTC 03/18/33/48) -> GitHub API workflow_dispatch -> bestehender `gold-v5-forward-paper.yml` im `main`-Zweig -> Checkout des `gold-bot-v3-9-5-test`-Zweigs -> unveränderte Paper-Strategie -> Telegram-Benachrichtigung.

Dieser Aufbau **verbessert den Auslöser**, nicht die garantierte Ausführungszeit des GitHub-Runners. Es ist keine vollständig unabhängige Ausführung. Cloudflare und GitHub sind ebenfalls best-effort. Keine Echtgeld-Orders.

## Vorbereitung
1. Ein Cloudflare-Konto und Wrangler CLI (aktuelles Node.js) werden benötigt.
2. Unter GitHub ein **fine-grained personal access token** für `ReneGold/gold-signal-bot` anlegen, mit *Actions: Read and write* und angemessenem Ablaufdatum. **Nicht hier im Chat teilen und nie in GitHub-Dateien speichern.**
3. In `external-scheduler/cloudflare` wechseln. Mit `npx wrangler login` Cloudflare autorisieren.
4. In `wrangler.jsonc` ggf. Worker-Konto/Projekt konfigurieren und mit `npx wrangler deploy` bereitstellen.
5. Mit `npx wrangler secret put GITHUB_WORKFLOW_TOKEN` den Token sicher hinterlegen (deployt eine neue Version).
6. Die Ausführung im Cloudflare-Dashboard prüfen; 204 = GitHub hat Dispatch angenommen.
7. Bei GitHub unter Actions prüfen, ob der **neue workflow_dispatch-Lauf** erfolgreich endet, im Testzweig den Forward-Bericht aktualisiert und Telegram ausschließlich beim neuen qualifizierten Paper-Signal benachrichtigt.

## Übergang und Rollback
- GitHub-Cron und Watchdog bleiben **bis zum bestätigten externen Test** unverändert aktiv.
- Danach ggf. GitHub-Cron als stündliches Backup reduzieren (separater geprüfter Commit). Bei Parallelstarts sorgt die vorhandene Workflow-Concurrency für Serialisierung, aber unnötige Doppelläufe bleiben möglich.
- Bei Störung den Cloudflare Cron Trigger deaktivieren, den GitHub-Cron unverändert weiterverwenden, Fehler anhand Logs prüfen.
- Monitoring und Marktstunden berücksichtigen Feiertage und die abweichenden Börsen-/Broker-Sessions nur näherungsweise.

## Sicherheitsgrenzen
- Der Worker hat **keinen öffentlichen Auslöse-Endpunkt**; HTTP-Anfragen erhalten 404.
- GitHub-Token nur als Cloudflare-Secret; keinen Token in Code oder Logs drucken.
- Authentifizierungsfehler und fehlende Secrets sind harte Fehler; bloße HTTP-204-Bestätigung ist **kein** erfolgreicher Paper-Trade.
- Keine rückwirkenden Trades, keine Replay-Signale, keine automatische Brokerorder.

## Unveränderte Grenzen
Der Gold-V5-Observer akzeptiert nur Kerzen innerhalb eines 15-Minuten-Frischefensters. Ein verspätet gestarteter GitHub-Job kann weiterhin Signale verpassen. Für echten unabhängigen 15-Minuten-Betrieb muss die **Berechnung selbst** auf einen laufenden externen Dienst mit dauerhafter Zustandsverwaltung umziehen.
