#!/usr/bin/env python3
"""Gold V5 paper-only Telegram notifier. Uses confirmed next-bar paper entry.
Never sends orders. Keeps sent signal IDs in JSON for deduplication.
"""
import argparse
import csv
import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
import requests

HERE=Path(__file__).resolve().parent
def select(rows, sent, now, max_age_minutes=90):
    out=[]
    for r in rows:
        if r.get("cohort")!="FORWARD" or r.get("status") not in ("OPEN_PAPER","CLOSED_PAPER"):
            continue
        key=r.get("signal_utc","")
        if not key or key in sent or not all(r.get(k) for k in ("entry","stop","target","entry_utc")):
            continue
        try:
            entry_time=datetime.fromisoformat(r["entry_utc"])
            if entry_time.tzinfo is None: continue
            age=now-entry_time.astimezone(timezone.utc)
            if age < timedelta(0) or age>timedelta(minutes=max_age_minutes): continue
            vals=[float(r[k]) for k in ("entry","stop","target")]
            if not all(__import__("math").isfinite(v) for v in vals): continue
        except (ValueError,TypeError): continue
        out.append(r)
    return sorted(out,key=lambda r:r["signal_utc"])

def format_message(r):
    direction="KAUFEN / LONG" if r["side"]=="LONG" else "VERKAUFEN / SHORT"
    return ("🟡 GOLD V5 – PAPER-SIGNAL (KEIN ECHTGELD)\n"
            f"{direction}\n"
            f"Signal: {r['signal_utc']}\n"
            f"Indikativer Einstieg: {float(r['entry']):.2f} USD\n"
            f"Stop-Loss: {float(r['stop']):.2f} USD\n"
            f"Take-Profit: {float(r['target']):.2f} USD\n"
            "Nur Modellwerte aus abgeschlossenen Kerzen; nicht broker-verifiziert.\n"
            "Keine automatische Order. Verspaetete Benachrichtigung moeglich.")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ledger",type=Path,default=HERE/"gold_v5_forward_ledger.csv")
    ap.add_argument("--state",type=Path,default=HERE/"gold_v5_telegram_sent.json")
    ap.add_argument("--test",action="store_true",help="Send explicit connectivity test, no trade")
    args=ap.parse_args()
    token=os.environ.get("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.environ.get("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat: raise SystemExit("Telegram secrets missing; not sent")
    state=json.loads(args.state.read_text(encoding="utf-8")) if args.state.exists() else {"sent":[]}
    sent=set(state.get("sent",[]))
    if args.test:
        messages=[(None,"🟡 Gold V5 Telegram Test OK – PAPER, kein Handelssignal.")]
    else:
        with args.ledger.open(newline="",encoding="utf-8-sig") as f:
            messages=[(r["signal_utc"],format_message(r)) for r in select(list(csv.DictReader(f)),sent,datetime.now(timezone.utc))]
    for key,message in messages:
        url=f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            response=requests.post(url,json={"chat_id":chat,"text":message},timeout=20)
            response.raise_for_status()
            if not response.json().get("ok"): raise RuntimeError("Telegram API returned not ok")
        except Exception as e:
            # Never print exception or response body: may expose token in URL.
            raise SystemExit("Telegram delivery failed; no send-state recorded") from None
        if key:
            sent.add(key)
            args.state.write_text(json.dumps({"sent":sorted(sent)},indent=2)+"\n",encoding="utf-8")
        print("Telegram message acknowledged", key or "TEST")
if __name__=="__main__":
    main()
