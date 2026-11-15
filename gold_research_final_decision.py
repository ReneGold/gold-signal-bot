#!/usr/bin/env python3
"""Final bounded Gold research: baseline vs ONE fixed UTC-session hypothesis.

Fixed before reading November performance:
- H0 = same V1 candidate traded all available hours.
- H1 = V1 candidate traded only if CLOSED 15m signal is 12:00–17:59 UTC.
This is an exploratory calendar heuristic, not a learned parameter.
Aug-Oct were already researched and are not an independent discovery sample.
Nov 1-14 is the only later holdout; short windows may be inconclusive.
No new entry/exit logic and no live trading.
"""
import argparse,json
from datetime import datetime,timezone
from pathlib import Path
from gold_research_v1_backtest import read_bars, quality, replay

HOURS=tuple(range(12,18))
CUT=datetime(2026,11,1,tzinfo=timezone.utc)
END=datetime(2026,11,15,tzinfo=timezone.utc)

def metrics(trades):
    net=[t["net_R"] for t in trades]
    gains=sum(max(0,x) for x in net)
    losses=-sum(min(0,x) for x in net)
    eq=peak=dd=0
    for r in net:eq+=r;peak=max(eq,peak);dd=max(dd,peak-eq)
    return {"trades":len(net),"wins":sum(x>0 for x in net),
            "net_R":round(eq,4),"mean_R":round(eq/len(net),4) if net else None,
            "profit_factor":round(gains/losses,3) if losses else None,
            "drawdown_R":round(dd,4)}

def group(trades):
    dev=[];hold=[]
    for t in trades:
        time=datetime.fromisoformat(t["signal_utc"])
        if time<CUT:dev.append(t)
        elif time<END:hold.append(t)
    return {"development_aug_oct":metrics(dev),"holdout_nov1_14":metrics(hold)}

def evaluate(b15,h1,cost,slippage):
    qa=quality(b15,h1)
    base=replay(b15,h1,cost,slippage)
    filtered=replay(b15,h1,cost,slippage,allowed_signal_hours_utc=set(HOURS))
    b=group(base["trades"])
    f=group(filtered["trades"])
    h=b["holdout_nov1_14"];fh=f["holdout_nov1_14"]
    # Conservative and explicit: no auto-release on sparse data.
    if h["trades"]<30 or fh["trades"]<30:
        verdict="INCONCLUSIVE_HOLDOUT_TOO_FEW_TRADES"
    elif not (h["mean_R"]>0 and fh["mean_R"]>0 and h["profit_factor"]>1.1 and fh["profit_factor"]>1.1):
        verdict="NO_POSITIVE_HOLDOUT_EDGE_DEMONSTRATED"
    elif fh["mean_R"]<=h["mean_R"]:
        verdict="SESSION_FILTER_DID_NOT_IMPROVE_HOLDOUT_EDGE"
    else:
        verdict="PROMISING_RESEARCH_ONLY_NEEDS_INDEPENDENT_LONGER_VALIDATION"
    if qa["h1_blocks_price_mismatch"] or qa["h1_blocks_unmatched_missing_15m"]:
        verdict="INVALID_DATA_ALIGNMENT"
    return {"status":verdict,"predeclared_hypothesis":"Signal close UTC hour in [12,18); no optimized parameters",
            "periods":{"development":"2026-08-01 to 2026-10-31 (already researched)",
                       "holdout":"2026-11-01 to 2026-11-14 (short, cannot prove edge)"},
            "source":"Dukascopy indicative bid OHLC; H1 derived from complete 15m candles",
            "cost":{"extra_roundtrip_usd_per_oz":cost,"slippage_each_side_usd_per_oz":slippage,
                    "broker_quote_verified":False},
            "data_quality":qa,
            "baseline":b,"one_filter":f,
            "candidate_gaps":{"baseline":len(base["unresolved"]),"one_filter":len(filtered["unresolved"])},
            "warnings":["No independent comparison of actual broker bid/ask spread/slippage; results not executable.",
                        "November data through 14th only; there may be too few holdout trades.",
                        "August-October history was studied and cannot be called independent.",
                        "Only one predeclared hour window is compared; no repeated filter search.",
                        "No profitability claim and no automatic strategy activation."]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bars15",type=Path,required=True)
    ap.add_argument("--bars1h",type=Path,required=True)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--cost",type=float,default=0.8)
    ap.add_argument("--slippage",type=float,default=0.0)
    a=ap.parse_args()
    if a.cost<0 or a.slippage<0:ap.error("Costs must be nonnegative")
    data=evaluate(read_bars(a.bars15),read_bars(a.bars1h),a.cost,a.slippage)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":data["status"],"baseline":data["baseline"],
                      "one_filter":data["one_filter"],"candidate_gaps":data["candidate_gaps"]},
                     ensure_ascii=False,indent=2))
if __name__=="__main__":main()
