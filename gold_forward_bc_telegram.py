"""Telegram notifications for NEW Gold B/C forward SHADOW signals only.
Never places orders. Uses existing GitHub Telegram secrets. A test-branch
delivery ledger suppresses repeat notifications across scheduled runs.
"""
import csv,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parent
SNAP=ROOT/"gold_forward_bc_snapshot.csv"
SENT=ROOT/"gold_forward_bc_telegram_sent.csv"
FIELDS=("signal_candle_utc","side","sent_at_utc")

def read_csv(path):
    if not path.exists():return []
    with path.open(newline="",encoding="utf-8") as f:return list(csv.DictReader(f))

def candidates(rows,already,now):
    selected=[]
    for r in rows:
        if r.get("side") not in ("LONG","SHORT"):continue
        if str(r.get("b_accepted"))!="1" and str(r.get("c_accepted"))!="1":continue
        key=(r["signal_candle_utc"],r["side"])
        if key in already:continue
        closed=datetime.fromisoformat(r["closed_at_utc"])
        # Never back-send old snapshots after first enabling Telegram.
        if closed.tzinfo is None or not timedelta(0)<=now-closed<=timedelta(minutes=35):continue
        selected.append(r)
        already.add(key)
    return selected

def message(r):
    accepted="B + C" if str(r["c_accepted"])=="1" else "B"
    direction="KAUF / LONG" if r["side"]=="LONG" else "VERKAUF / SHORT"
    def fmt(x):
        try:return f"{float(x):,.2f}"
        except (ValueError,TypeError):return "nicht verfügbar"
    return ("🟡 GOLD XAU/USD – NEUES V4-TESTSIGNAL\n"
            f"Richtung: {direction}\n"
            f"Strategie: {accepted}\n"
            f"Score: {r.get('score','?')}\n"
            f"Signal-Schluss (UTC): {r['closed_at_utc']}\n"
            f"Referenzkurs: {fmt(r.get('bar_close'))}\n"
            f"Stop-Loss: {fmt(r.get('stop'))}\n"
            f"TP1: {fmt(r.get('tp1'))}\n"
            f"TP2: {fmt(r.get('tp2'))}\n"
            f"TP3: {fmt(r.get('tp3'))}\n\n"
            "⚠️ Nur Forschungs-/Demo-Signal, keine Order. "
            "Kurse sind indikativ, Einstieg und Broker-Ausführung nicht bestätigt.")

def main():
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:
        raise RuntimeError("Telegram secrets missing; refuse silent notification failure")
    now=datetime.now(timezone.utc)
    sent=read_csv(SENT);already={(r["signal_candle_utc"],r["side"]) for r in sent}
    pending=candidates(read_csv(SNAP),already,now)
    for r in pending:
        response=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id":chat,"text":message(r)},timeout=20)
        response.raise_for_status()
        if not response.json().get("ok"):raise RuntimeError("Telegram API rejected message")
        sent.append({"signal_candle_utc":r["signal_candle_utc"],
                     "side":r["side"],"sent_at_utc":now.isoformat()})
        # Persist after every successful send in case later HTTP calls fail.
        with SENT.open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(sent)
    print(f"Gold B/C Telegram: sent={len(pending)} cumulative={len(sent)} (only new test signals)")
    print("No test message sent when there is no qualifying signal.")
if __name__=="__main__":main()
