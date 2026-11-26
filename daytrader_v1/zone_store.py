"""SQLite registry for confirmed Fibonacci zones and paper signal reservations.
No scheduler, order execution or delivery. Use a persistent local database.
All timestamps are UTC epoch seconds. One database per feed/account.
"""
import hashlib
import json
import sqlite3
from contextlib import contextmanager
from math import isfinite

TERMINAL = frozenset(("INVALIDATED","EXPIRED","SIGNALLED"))

def identity(z):
    if z["side"] not in ("BUY","SELL"):
        raise ValueError("invalid side")
    for k in ("start_time","end_time","confirmed_at"):
        if type(z[k]) is not int or z[k]<=0:
            raise ValueError("invalid timestamp")
    if not z["start_time"]<z["end_time"]<=z["confirmed_at"]:
        raise ValueError("invalid chronology")
    for k in ("start","end","lower","upper"):
        if type(z[k]) not in (int,float) or not isfinite(z[k]) or z[k]<=0:
            raise ValueError("invalid zone price")
    if not min(z["start"],z["end"])<z["lower"]<z["upper"]<max(z["start"],z["end"]):
        raise ValueError("invalid zone bounds")
    if (z["end"]>z["start"]) != (z["side"]=="BUY"):
        raise ValueError("invalid impulse")
    raw=json.dumps(["XAUUSD",z["side"],z["start_time"],z["end_time"]],separators=(",",":"))
    return hashlib.sha256(raw.encode()).hexdigest()

class ZoneStore:
    def __init__(self,path):
        self.path=path
        with self.transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS zones(
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, status TEXT NOT NULL,
                last_seen INTEGER NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS signals(
                zone_id TEXT PRIMARY KEY REFERENCES zones(id),
                candle_time INTEGER NOT NULL UNIQUE, payload TEXT NOT NULL)""")
    @contextmanager
    def transaction(self):
        db=sqlite3.connect(self.path,timeout=15,isolation_level=None)
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
    def register(self,z,now):
        key=identity(z)
        if type(now) is not int or now<z["confirmed_at"]:
            raise ValueError("zone not yet confirmed")
        payload=json.dumps(z,sort_keys=True,allow_nan=False)
        with self.transaction() as db:
            existing=db.execute("SELECT payload FROM zones WHERE id=?",(key,)).fetchone()
            if existing and existing[0]!=payload:
                raise ValueError("historical zone revision")
            db.execute("INSERT OR IGNORE INTO zones VALUES(?,?,?,?)",
                       (key,payload,"WAIT",z["confirmed_at"]))
        return key
    def active(self):
        with self.transaction() as db:
            rows=db.execute("SELECT id,payload,status,last_seen FROM zones WHERE status IN ('WAIT','TOUCHED','CANDIDATE') ORDER BY last_seen,id").fetchall()
        return [dict(id=k,zone=json.loads(p),status=s,last_seen=t) for k,p,s,t in rows]
    def update(self,key,status,candle_time):
        if status not in ("WAIT","TOUCHED","CANDIDATE","INVALIDATED","EXPIRED"):
            raise ValueError("invalid observation status")
        if type(candle_time) is not int:
            raise ValueError("invalid observation time")
        with self.transaction() as db:
            row=db.execute("SELECT status,last_seen FROM zones WHERE id=?",(key,)).fetchone()
            if not row or row[0] in TERMINAL or candle_time<=row[1]:
                return False
            db.execute("UPDATE zones SET status=?,last_seen=? WHERE id=?",(status,candle_time,key))
            return True
    def reserve_signal(self,key,candle_time,decision,now):
        """Atomic deduplication, not an order or a guarantee of Telegram delivery."""
        if decision.get("mode")!="PAPER" or decision.get("signal") not in ("BUY","SELL"):
            return False
        if type(now) is not int or type(candle_time) is not int:
            return False
        if not candle_time<=now<=decision.get("valid_until",-1) or now-candle_time>60:
            return False
        if decision.get("timestamp")!=now or decision.get("instrument")!="XAUUSD":
            return False
        if not decision.get("score",0)>=80 or not decision.get("net_rr",0)>=2:
            return False
        with self.transaction() as db:
            row=db.execute("SELECT status,last_seen,payload FROM zones WHERE id=?",(key,)).fetchone()
            if not row or row[0]!="CANDIDATE" or row[1]!=candle_time:
                return False
            if json.loads(row[2])["side"]!=decision["signal"] or decision.get("zone")!=json.loads(row[2]):
                return False
            payload=json.dumps(decision,sort_keys=True,allow_nan=False)
            cursor=db.execute("INSERT OR IGNORE INTO signals VALUES(?,?,?)",(key,candle_time,payload))
            if cursor.rowcount!=1:
                return False
            db.execute("UPDATE zones SET status='SIGNALLED' WHERE id=?",(key,))
            return True
