#!/usr/bin/env python3
"""Gold Research V1 historical *research* replay; no trading, network, or alerts.

Requires UTC 15m and H1 OHLC CSV. Signals use ONLY finished bars; next-bar open
fills are indicative and cannot substitute for real broker bid/ask quotes.
Candidate logic is imported unchanged from gold_research_v1.py.
"""
import argparse, bisect, csv, json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from gold_research_v1 import Bar, candidate

def read_bars(path):
    rows=[]
    with path.open(newline="", encoding="utf-8-sig") as f:
        for line in csv.DictReader(f):
            dt=datetime.fromisoformat(line["timestamp"].replace("Z","+00:00"))
            if dt.tzinfo is None or dt.utcoffset()!=timedelta(0):
                raise ValueError("Only UTC candle OPEN timestamps")
            rows.append(Bar(dt,*(float(line[k]) for k in ("open","high","low","close"))))
    if any(y.start<=x.start for x,y in zip(rows,rows[1:])):
        raise ValueError("Non-increasing or duplicate candles")
    return rows

def quality(b15,h1):
    intervals15=Counter(int((y.start-x.start).total_seconds()/60) for x,y in zip(b15,b15[1:]))
    intervals60=Counter(int((y.start-x.start).total_seconds()/60) for x,y in zip(h1,h1[1:]))
    # Compare H1 OHLC to aggregated 4x15m bars from the exact same provider.
    fifteen={b.start:b for b in b15}
    matched=mismatch=missing=0
    examples=[]
    for h in h1:
        candles=[fifteen.get(h.start+timedelta(minutes=15*k)) for k in range(4)]
        if any(x is None for x in candles):
            missing+=1;continue
        matched+=1
        c=[x for x in candles if x is not None]
        expected=(c[0].open,max(x.high for x in c),min(x.low for x in c),c[-1].close)
        actual=(h.open,h.high,h.low,h.close)
        if any(abs(a-b)>max(0.05,abs(a)*0.00002) for a,b in zip(actual,expected)):
            mismatch+=1
            if len(examples)<3:examples.append({"h1_start":h.start.isoformat(),
                                                 "h1":actual,"from_15m":expected})
    return {"bars_15m":len(b15),"bars_h1":len(h1),
            "first_15m":b15[0].start.isoformat() if b15 else None,
            "last_15m":b15[-1].start.isoformat() if b15 else None,
            "intervals_15m_minutes":dict(sorted(intervals15.items())),
            "intervals_h1_minutes":dict(sorted(intervals60.items())),
            "h1_blocks_with_all_four_15m":matched,
            "h1_blocks_unmatched_missing_15m":missing,
            "h1_blocks_price_mismatch":mismatch,"mismatch_examples":examples}

def replay(b15,h1,extra_round_trip=0.8,adverse_each_side=0.0,allowed_signal_hours_utc=None):
    if extra_round_trip<0 or adverse_each_side<0:raise ValueError("Negative cost")
    if len(b15)<200 or len(h1)<90:raise ValueError("Too little input")
    closeh=[b.start+timedelta(hours=1) for b in h1]
    trades=[]
    rejected=Counter()
    unresolved=[]
    no_overlap_until=0
    for i in range(100,len(b15)-17):
        if i<no_overlap_until:continue
        close_time=b15[i].start+timedelta(minutes=15)
        if allowed_signal_hours_utc is not None and close_time.hour not in allowed_signal_hours_utc:
            rejected["OUTSIDE_PREDECLARED_UTC_SESSION"]+=1
            continue
        if b15[i+1].start != close_time:
            rejected["NO_NEXT_BAR_OPEN"]=rejected["NO_NEXT_BAR_OPEN"]+1
            continue
        j=bisect.bisect_right(closeh,close_time)-1
        if j<79:continue
        try:
            result=candidate(b15[i-79:i+1],h1[j-79:j+1],close_time)
        except ValueError:
            rejected["DATA_WINDOW_INVALID"]+=1
            continue
        if result["status"]!="PAPER_CANDIDATE":
            rejected[result["reason"]]+=1;continue
        d=1 if result["side"]=="LONG" else -1
        risk=result["indicative_stop_distance"]
        fill=b15[i+1].open+d*adverse_each_side
        sl=fill-d*risk
        tp=fill+d*2*risk
        exit_price=None
        why=None
        k_last=None
        bad_gap=False
        for k in range(i+1,i+17):
            if k>i+1 and b15[k].start-b15[k-1].start!=timedelta(minutes=15):
                bad_gap=True;break
            candle=b15[k]
            hit_stop=(candle.low<=sl if d==1 else candle.high>=sl)
            hit_target=(candle.high>=tp if d==1 else candle.low<=tp)
            if hit_stop:
                exit_price=min(sl,candle.open) if d==1 else max(sl,candle.open)
                why="STOP";k_last=k;break
            if hit_target:
                exit_price=tp;why="TARGET";k_last=k;break
            exit_price=candle.close;k_last=k
        if bad_gap:
            unresolved.append({"signal_utc":close_time.isoformat(),"reason":"EXIT_PRICE_GAP"})
            no_overlap_until=k+1
            continue
        if k_last is None:raise RuntimeError("Exit state failure")
        if why is None:why="TIME_16_BARS"
        # Adverse exit slippage and roundtrip cost expressed in XAUUSD price units.
        net_r=(d*(exit_price-fill)-adverse_each_side-extra_round_trip)/risk
        trades.append({"signal_utc":close_time.isoformat(),"side":result["side"],
                       "entry_utc":b15[i+1].start.isoformat(),
                       "entry":round(fill,6),"sl":round(sl,6),"tp":round(tp,6),
                       "exit_utc":b15[k_last].start.isoformat(),"exit_reason":why,
                       "net_R":round(net_r,6)})
        no_overlap_until=k_last+1
    gains=sum(max(0,t["net_R"]) for t in trades)
    losses=-sum(min(0,t["net_R"]) for t in trades)
    balance=peak=dd=0.
    for trade in trades:
        balance+=trade["net_R"];peak=max(peak,balance);dd=max(dd,peak-balance)
    stats={"trades":len(trades),"wins":sum(t["net_R"]>0 for t in trades),
           "net_R":round(balance,4),"average_R":round(balance/len(trades),4) if trades else None,
           "profit_factor":round(gains/losses,3) if losses else None,
           "max_closed_drawdown_R":round(dd,4),"unresolved_exit_gaps":len(unresolved)}
    return {"stats":stats,"rejections":dict(rejected),"unresolved":unresolved,"trades":trades}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--bars15",type=Path,required=True)
    p.add_argument("--bars1h",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--cost",type=float,default=0.8)
    p.add_argument("--slippage",type=float,default=0)
    args=p.parse_args()
    b15,h1=read_bars(args.bars15),read_bars(args.bars1h)
    qa=quality(b15,h1)
    back=replay(b15,h1,args.cost,args.slippage)
    result={"strategy":"Gold Research V1 – H1 trend, 15m breakout of prior 20",
            "test_type":"EXPLORATORY_IN_SAMPLE_NOT_FORWARD",
            "data_source":"Dukascopy indicative BID candles, XAUUSD (not PU Prime)",
            "data_quality":qa,
            "cost_assumptions":{"extra_roundtrip_usd_per_oz":args.cost,
                "adverse_slippage_each_side_usd_per_oz":args.slippage,
                "broker_spread_verified":False},
            "limitations":["Trading hours and session closures must be broker-verified.",
                "No tick-by-tick prices or executable broker spreads; stop-first on ambiguous bars.",
                "A trading strategy is not proven profitable by this test.",
                "No news, real-time latency, financing, funding or broker margin model.",
                "Initial August-October sample is exploratory and not independent out-of-sample."],
            **back}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"data_quality":qa,"stats":back["stats"],
        "rejections":back["rejections"],"cost_assumptions":result["cost_assumptions"]},
        ensure_ascii=False,indent=2))
if __name__=="__main__":main()
