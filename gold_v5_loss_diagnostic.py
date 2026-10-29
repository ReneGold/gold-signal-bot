#!/usr/bin/env python3
"""Research-only diagnostic: replay the existing V5 session A/B trades with original OHLC.
No execution, no Telegram, no optimization and no change to the running bots.
MFE/MAE are descriptive intrabar extremes, not evidence of achievable fills.
"""
import csv,json,statistics
from collections import defaultdict,Counter
from datetime import datetime
from pathlib import Path

P=Path(__file__).resolve().parent/"gold_data_audit"
with (P/"gold_15min_2026_aug_oct.csv").open(encoding="utf-8",newline="") as f:
    candles=list(csv.DictReader(f))
with (P/"gold_v5_session_ab_trades.csv").open(encoding="utf-8",newline="") as f:
    trades=list(csv.DictReader(f))
index={r["utc"]:i for i,r in enumerate(candles)}
def quant(values):
    if not values:return None
    return round(statistics.median(values),4)
details=[];issues=Counter()
for tr in trades:
    si=index.get(tr["entry_utc"]);ei=index.get(tr["exit_utc"])
    if si is None or ei is None or ei<si:
        issues["unmatched_or_reversed_time"]+=1;continue
    direction=1 if tr["side"]=="LONG" else -1
    entry=float(tr["entry"]);exitprice=float(tr["exit"])
    highs=[float(x["high"]) for x in candles[si:ei+1]]
    lows=[float(x["low"]) for x in candles[si:ei+1]]
    favorable=(max(highs)-entry) if direction==1 else (entry-min(lows))
    adverse=(entry-min(lows)) if direction==1 else (max(highs)-entry)
    r=float(tr["net_R"])
    # Existing backtest assumed 0.8 USD/oz total cost and 1.5 ATR initial stop:
    # for STOP trades, stops may gap beyond risk. For all trades approximate initial
    # risk by reproducing Wilder ATR at signal candle from entire original history.
    details.append({**tr,"net_R":round(r,5),"favorable_usd":round(favorable,5),
        "adverse_usd":round(adverse,5),"bars_held":ei-si+1,
        "exit_month_utc":datetime.fromisoformat(tr["exit_utc"]).strftime("%Y-%m"),
        "entry_hour_utc":datetime.fromisoformat(tr["entry_utc"]).hour})
# summary by strategy / session / side / calendar month
def stats(a):
    gain=sum(max(0,float(x["net_R"])) for x in a)
    loss=-sum(min(0,float(x["net_R"])) for x in a)
    return {"trades":len(a),"sum_net_R":round(sum(float(x["net_R"]) for x in a),4),
            "win_pct":round(100*sum(float(x["net_R"])>0 for x in a)/len(a),2) if a else None,
            "profit_factor":round(gain/loss,3) if loss else None,
            "median_favorable_usd":quant([x["favorable_usd"] for x in a]),
            "median_adverse_usd":quant([x["adverse_usd"] for x in a]),
            "median_bars_held":quant([x["bars_held"] for x in a]),
            "exit_reasons":dict(Counter(x["exit_reason"] for x in a))}
report={"dataset":"Gold V5 earlier session A/B research backtest, 2026 Aug-Oct",
 "limitations":["Same historical sample; NOT out-of-sample or live profitability",
 "Uses provided previous backtest exits; fill assumptions and bar ambiguity remain",
 "MFE/MAE derived from candle highs/lows including exit bar; cannot infer tradeable exits",
 "Original source includes weekend indicative bars; CME reference not guaranteed spot-tradeable",
 "No 1h regime classification in this diagnostic: avoid claiming market-phase attribution",
 "Comparing risk-adjusted R across months is approximate due to changing ATR and gap fills"],
 "records_analyzed":len(details),"unmatched":dict(issues),"groups":[]}
for rule in sorted(set(x["rule"] for x in details)):
 for session in sorted(set(x["session_filter"] for x in details)):
  sample=[x for x in details if x["rule"]==rule and x["session_filter"]==session]
  if not sample:continue
  group={"rule":rule,"session":session,"overall":stats(sample),
         "by_side":{v:stats([x for x in sample if x["side"]==v]) for v in ("LONG","SHORT")},
         "by_exit_month":{v:stats([x for x in sample if x["exit_month_utc"]==v]) for v in sorted(set(x["exit_month_utc"] for x in sample))},
         "by_entry_hour_utc":{str(v):stats([x for x in sample if x["entry_hour_utc"]==v]) for v in sorted(set(x["entry_hour_utc"] for x in sample))}}
  report["groups"].append(group)
  print(rule,session,"total",group["overall"]["sum_net_R"],"n",group["overall"]["trades"],
        "LONG",group["by_side"]["LONG"]["sum_net_R"],"SHORT",group["by_side"]["SHORT"]["sum_net_R"])
with (P/"gold_v5_loss_diagnostic.json").open("w",encoding="utf-8") as f:json.dump(report,f,indent=2,ensure_ascii=False)
with (P/"gold_v5_loss_trade_details.csv").open("w",encoding="utf-8",newline="") as f:
    fields=["rule","session_filter","signal_utc","entry_utc","exit_utc","side","entry","exit",
      "net_R","exit_reason","favorable_usd","adverse_usd","bars_held","exit_month_utc","entry_hour_utc"]
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(details)
print("Analyzed",len(details),"historical simulated trades; no live-bot changes.")
