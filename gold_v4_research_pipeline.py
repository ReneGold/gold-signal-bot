"""V4 research-only integration of five modules. No broker/Telegram interactions.
A B/C signal must be supplied by existing shadow detector; the caller supplies
real closed 15m/5m bars, real calendar status, and explicit risk inputs.
UNKNOWN news or missing required inputs => NOT_READY, never an approval.
"""
from gold_risk_manager import check_trade
from gold_news_volatility_filter import check as news_check
from gold_entry_timer import assess_entry
from gold_exit_planner import Plan,new_position
from gold_time_machine import analyze

def evaluate(*,variant,side,entry,stop,score,signal_close_utc,asof_utc,
             fifteen_bars,signal_index,five_bars,atr_15m,events,
             calendar_verified,equity,day_realized_pnl,quantity_oz,
             open_positions,position_currency_matches_account):
    if variant not in ("B","C") or side not in ("LONG","SHORT") or score<65:
        return {"status":"REJECTED","reasons":["No eligible B/C Score 65 setup"]}
    if (not calendar_verified or not position_currency_matches_account
        or not fifteen_bars or signal_index!=len(fifteen_bars)-1):
        return {"status":"NOT_READY","reasons":["Unverified calendar, currency conversion or candle completeness"]}
    last=fifteen_bars[signal_index]
    if last.t.tzinfo is None or last.t.replace(tzinfo=None)>signal_close_utc.replace(tzinfo=None):
        return {"status":"NOT_READY","reasons":["Invalid candle timestamp"]}
    risk=check_trade(equity=equity,day_realized_pnl=day_realized_pnl,
        entry=entry,stop=stop,target=entry+(1 if side=="LONG" else -1)*2.25*abs(entry-stop),
        quantity_oz=quantity_oz,open_positions=open_positions)
    if not risk["approved"]:return {"status":"REJECTED","stage":"RISK","reasons":risk["reasons"]}
    import math
    tr=max(last.h-last.l,abs(last.h-fifteen_bars[signal_index-1].c),
           abs(last.l-fifteen_bars[signal_index-1].c))
    news=news_check(assessed_at_utc=asof_utc,events=events,latest_close=last.c,
                    latest_true_range=tr,atr_15m=atr_15m)
    if not news["approved"]:return {"status":"REJECTED","stage":"NEWS_VOL","reasons":news["reasons"]}
    direction=1 if side=="LONG" else -1
    timer=assess_entry(setup_close_utc=signal_close_utc,side=side,
        trigger=entry,invalid_level=stop,five_minute_bars=five_bars,now_utc=asof_utc)
    if timer["status"]!="CONFIRMED":
        return {"status":"NOT_READY" if timer["status"]=="WAITING" else "REJECTED",
                "stage":"ENTRY_TIMER","reasons":[timer["reason"]]}
    plan=Plan(entry,stop,direction)
    bars=[__import__("gold_time_machine").Bar(b.o,b.h,b.l,b.c) for b in fifteen_bars]
    history=analyze(bars,signal_index,direction,abs(entry-stop))
    return {"status":"RESEARCH_CANDIDATE","variant":variant,"score":score,
            "risk":risk,"calendar":news["calendar_status"],
            "entry_confirmation":timer,"exit_targets":plan.targets,
            "exit_portions":plan.portions,"time_machine":history,
            "paper_state":new_position(plan),
            "warning":"No order, no live approval; historical analog scores are uncalibrated"}
