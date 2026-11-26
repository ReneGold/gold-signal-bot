"""Opt-in Telegram transport for reserved paper signals only.
Delivery is at-most-one attempted send per reservation when using dispatch().
Ambiguous network outcomes are recorded, never automatically retried.
"""
import os
import json
import sqlite3
import time
from datetime import datetime, timezone
from math import isfinite
import requests

def message(d):
    if d.get("mode")!="PAPER" or d.get("instrument")!="XAUUSD" or d.get("signal") not in ("BUY","SELL"):
        raise ValueError("not a paper signal")
    e,sl,tp,rr,score=(float(d[k]) for k in ("entry","stop","target","net_rr","score"))
    if not all(isfinite(x) for x in (e,sl,tp,rr,score)) or min(e,sl,tp)<=0 or not 80<=score<=100 or rr<2:
        raise ValueError("invalid paper signal")
    if not (sl<e<tp if d["signal"]=="BUY" else tp<e<sl):
        raise ValueError("invalid price geometry")
    stamp,expiry=d["timestamp"],d["valid_until"]
    if type(stamp) is not int or type(expiry) is not int or not 0<expiry-stamp<=60:
        raise ValueError("invalid validity")
    fmt=lambda t: datetime.fromtimestamp(t,timezone.utc).strftime("%d.%m.%Y %H:%M:%S UTC")
    return (f"GOLD AI DAYTRADER 1.0 | PAPER\n"
            f"XAUUSD | {d['signal']}\n"
            f"Entry: {e:.2f} USD\nStop-Loss: {sl:.2f} USD\nTake-Profit: {tp:.2f} USD\n"
            f"CRV nach Kosten: 1:{rr:.2f}\nScore: {score:g}/100\n"
            f"Setup: Trend-Pullback\nSignal: {fmt(stamp)}\nGültig bis: {fmt(expiry)}\n"
            "Nur Simulation. Bei Kursabweichung oder geänderten Risikobedingungen ungültig. Keine Order.")

def dispatch(store, zone_id, http=None, clock=time.time):
    if os.getenv("DAYTRADER_V1_TELEGRAM_ENABLED")!="1":
        return "DISABLED"
    token=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat=os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat:
        return "MISSING_CONFIG"
    http=http or requests
    with store.transaction() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS telegram_delivery(
            zone_id TEXT PRIMARY KEY REFERENCES signals(zone_id),
            status TEXT NOT NULL, attempted_at INTEGER NOT NULL,
            message_id TEXT)""")
        row=db.execute("SELECT payload FROM signals WHERE zone_id=?",(zone_id,)).fetchone()
        if not row:
            return "NOT_RESERVED"
        d=json.loads(row[0])
        body=message(d)
        now=int(clock())
        if not d["timestamp"]<=now<=d["valid_until"]:
            return "EXPIRED"
        cur=db.execute("INSERT OR IGNORE INTO telegram_delivery VALUES(?,?,?,NULL)",
                       (zone_id,"ATTEMPTED",now))
        if cur.rowcount!=1:
            return "ALREADY_ATTEMPTED"
    status,mid="UNKNOWN",None
    try:
        if int(clock())>d["valid_until"]:
            status="EXPIRED"
        else:
            response=http.post(f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id":chat,"text":body},timeout=5)
            response.raise_for_status()
            payload=response.json()
            if payload.get("ok") is True and payload.get("result",{}).get("message_id") is not None:
                status,mid="SENT",str(payload["result"]["message_id"])
            elif payload.get("ok") is False:
                status="REJECTED"
    except (requests.RequestException,ValueError,TypeError,AttributeError):
        # Never log exceptions containing the bot token.
        status="UNKNOWN"
    with store.transaction() as db:
        db.execute("UPDATE telegram_delivery SET status=?,message_id=? WHERE zone_id=?",
                   (status,mid,zone_id))
    return status
