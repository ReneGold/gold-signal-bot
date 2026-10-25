#!/usr/bin/env python3
"""Read live Twelve Data bars + real B/C snapshots into V4 research-only interface.
Never sends messages, places orders, or treats missing news/account data as verified.
"""
import csv,json,os,sys,importlib.util
from datetime import datetime,timedelta,timezone
from pathlib import Path
from gold_v4_research_pipeline import evaluate
from gold_v4_free_calendar import retrieve as fetch_calendar
from gold_news_volatility_filter import check as volatility_news_gate
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v4_bot_data_only",P/"gold_signal_bot_v3_9_5_diagnose (2).py")
bot=importlib.util.module_from_spec(spec);sys.modules[spec.name]=bot;spec.loader.exec_module(bot)
from gold_entry_timer import Candle
def read_snapshot(path):
    with open(path,newline="",encoding="utf-8") as f:return list(csv.DictReader(f))
def scan(snapshot,c15,c5,atr,calendar=None):
    results=[]
    calendar=calendar or {"verified":False,"events":[],"status":"CALENDAR_UNAVAILABLE"}
    index={bar.t.isoformat():i for i,bar in enumerate(c15)}
    for row in snapshot:
        for variant,column in (("B","b_accepted"),("C","c_accepted")):
            if row[column]!="1" or row["side"]=="NONE":continue
            key=row["signal_candle_utc"]
            record=dict(variant=variant,signal_candle_utc=key,side=row["side"],score=row["score"],calendar_status=calendar["status"],calendar_verified=calendar["verified"])
            i=index.get(key)
            if i is None or i<4:
                record.update(status="NOT_READY",reasons=["Signal candle not in 15m feed"])
                results.append(record);continue
            b=c15[i]
            close_time=b.t+timedelta(minutes=15)
            asof=datetime.now(timezone.utc)
            # An OHLC feed may contain a forming bar; never pass it as confirmation.
            closed5=[Candle(v.t,v.o,v.h,v.l,v.c) for v in c5
                     if v.t+timedelta(minutes=5)<=asof and v.t>=close_time]
            if not closed5:
                record.update(status="NOT_READY",reasons=["No completed 5m candles after 15m setup"])
                results.append(record);continue
            try:
                prior=c15[i-1]
                tr=max(b.h-b.l,abs(b.h-prior.c),abs(b.l-prior.c))
                ng=volatility_news_gate(assessed_at_utc=asof,events=calendar["events"],
                    latest_close=b.c,latest_true_range=tr,atr_15m=atr[i])
                record["news_window_blocked"]="HIGH_IMPACT_USD_NEWS_WINDOW" in ng["reasons"]
                record["news_nearby"]=ng["nearby_high_impact_usd_events"]
                record["volatility_reasons"]=ng["reasons"]
                # Calendar, account equity/currency and live broker lots are intentionally
                # unverified; gate MUST return NOT_READY instead of approving.
                decision=evaluate(variant=variant,side=row["side"],entry=float(row["bar_close"]),
                    stop=float(row["stop"]),score=int(row["score"]),
                    signal_close_utc=close_time,asof_utc=asof,
                    fifteen_bars=c15[:i+1],signal_index=i,five_bars=closed5,
                    atr_15m=atr[i],events=calendar["events"],calendar_verified=calendar["verified"],
                    equity=5000.0,day_realized_pnl=0.0,quantity_oz=1.0,
                    open_positions=0,position_currency_matches_account=False)
                record.update(status=decision["status"],reasons=decision.get("reasons",[]))
            except (ValueError,IndexError,TypeError) as exc:
                record.update(status="NOT_READY",reasons=["Invalid/missing input: "+str(exc)])
            results.append(record)
    return results
if __name__=="__main__":
    snapshots=read_snapshot(P/"gold_forward_bc_snapshot.csv")
    if not snapshots:raise RuntimeError("No observation rows")
    c15=bot.candles("15min",320)
    c5=bot.candles("5min",300)
    if len(c15)<100 or len(c5)<10:raise RuntimeError("Insufficient real candle data")
    _,_,atr=bot.indicators(c15)
    calendar=fetch_calendar()
    records=scan(snapshots,c15,c5,atr,calendar)
    dest=P/"gold_v4_market_observation.json"
    dest.write_text(json.dumps({"generated_utc":datetime.now(timezone.utc).isoformat(),
        "feed":"Twelve Data 15min and 5min","calendar_verified":calendar["verified"],
        "calendar_status":calendar["status"],"calendar_raw_count":calendar.get("raw_count"),
        "calendar_high_us_count":calendar.get("us_high_count"),
        "calendar_uncertain_count":len(calendar.get("uncertain",[])),
        "calendar_attribution":calendar.get("attribution"),
        "calendar_high_impact_events":[{"name":e.name,"time_utc":e.time_utc.isoformat()} for e in calendar["events"]],
        "broker_account_verified":False,"observations":records},indent=2),encoding="utf-8")
    print("Free US calendar:",calendar["status"],"events",len(calendar["events"]),"unverified")
    print("Real Gold candle pipeline: B/C candidates =",len(records),
          "; no automated trading, calendar/broker unverified")
    for r in records:print(r["variant"],r["signal_candle_utc"],r["status"],r["reasons"])
