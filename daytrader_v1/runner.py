"""One explicit paper cycle. No scheduler, no live orders, no implicit verification.
External adapters supply verified snapshots; disabled by default.
Run serially per persistent account database.
"""
import os,json
from datetime import datetime,timezone
from math import isfinite
from .engine import evaluate
from .calendar_gate import evaluate_calendar
from .zone_store import ZoneStore
from .journal import Journal
from .paper_execution import PaperExecution,validate_quote,valid_cost
from .pullback import observe
from .telegram import dispatch

def risk_snapshot(store,now,initial_equity):
    if type(initial_equity) not in (float,int) or not isfinite(initial_equity) or initial_equity<=0:
        raise ValueError("invalid initial equity")
    day=now-now%86400
    with store.transaction() as db:
        pnl=db.execute("SELECT COALESCE(SUM(pnl),0) FROM paper_exits").fetchone()[0]
        daily=db.execute("SELECT pnl FROM paper_exits WHERE filled_at>=? AND filled_at<=? ORDER BY filled_at,zone_id",(day,now)).fetchall()
        used=db.execute("SELECT COALESCE(SUM(risk_usd),0) FROM paper_entries WHERE filled_at>=? AND filled_at<=?",(day,now)).fetchone()[0]
        opened=db.execute("SELECT COUNT(*) FROM paper_entries e LEFT JOIN paper_exits x USING(zone_id) WHERE x.zone_id IS NULL").fetchone()[0]
    streak=0
    for row in reversed(daily):
        if row[0]>=0: break
        streak+=1
    return dict(as_of=now,verified=True,equity_usd=initial_equity+pnl,
                daily_planned_risk_usd=used,open_positions=opened,
                daily_loss_count=sum(x[0]<0 for x in daily),loss_streak=streak)

def cycle(db_path,now,feed,quote,calendar,hours,initial_equity,cost,slippage):
    result=dict(mode="PAPER",signal="NO TRADE",timestamp=now)
    if os.getenv("DAYTRADER_V1_ENABLED")!="1":
        return dict(result,reason="DISABLED")
    if not all(valid_cost(x) for x in (cost,slippage)):
        return dict(result,reason="INVALID_COST")
    store=ZoneStore(db_path)
    journal=Journal(store)
    execution=PaperExecution(journal)
    try:
        t,bid,ask=validate_quote(quote,now)
    except (ValueError,KeyError,TypeError):
        return dict(result,reason="UNVERIFIED_QUOTE")
    # Existing positions take priority over new signals.
    risk=risk_snapshot(store,now,initial_equity)
    if risk["open_positions"]:
        return dict(result,reason="POSITION_MONITOR",
                    execution=execution.monitor(quote,now,hours,cost,slippage))
    gates=evaluate_calendar(now,calendar,hours)
    gates["as_of"]=now
    if feed.get("as_of")!=now or feed.get("data_verified") is not True:
        return dict(result,reason="UNVERIFIED_FEED")
    frames=feed["frames"]
    context=dict(risk,instrument="XAUUSD",now=now,data_verified=True,
                 risk_verified=True,news_clear=gates["news_clear"],
                 session_clear=gates["session_clear"],spread_clear=True,
                 session_start=gates["session_start"],volume_kind=feed.get("volume_kind"),
                 bid=bid,ask=ask,quote_time=t,cost_per_ounce=cost+2*slippage)
    d=evaluate(frames,context)
    # Only use structurally validated evaluation results to update zones.
    z=d.get("zone")
    if not z or "observation" not in d:
        return d
    key=store.register(z,now)
    candle=frames["m5"][-1]["timestamp"]
    for item in store.active():
        old=item["zone"]
        if frames["m5"][0]["timestamp"]>old["confirmed_at"]:
            continue
        obs=observe(old,frames["m5"])
        if obs["status"] in ("WAIT","TOUCHED","CANDIDATE","INVALIDATED","EXPIRED"):
            store.update(item["id"],obs["status"],candle)
    if d["signal"] not in ("BUY","SELL"):
        return d
    # Revalidate signal age and preserve atomic reservation.
    if not store.reserve_signal(key,candle,d,now):
        return dict(result,reason="DUPLICATE_OR_INVALID_RESERVATION")
    # A reserved signal is not a fill. Entry can be refused independently.
    status=execution.enter(key,quote,now,gates,risk,cost,slippage)
    d["execution"]=status
    d["zone_id"]=key
    # Send only if simulated entry was accepted, and only while still valid.
    d["telegram"]=dispatch(store,key) if status=="PAPER_FILLED" else "NOT_FILLED"
    return d
