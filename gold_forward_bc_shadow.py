#!/usr/bin/env python3
"""Prospective, observation-only Score 65 B/C candle snapshots. No orders/Telegram/state changes."""
import contextlib,csv,importlib.util,io,os
from datetime import datetime,timedelta,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
f=P/"gold_signal_bot_v3_9_5_diagnose (2).py"
spec=importlib.util.spec_from_file_location("shadow_bot",f)
bot=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=bot
spec.loader.exec_module(bot)
bot.MIN_SCORE=65
bot.send=lambda *args,**kwargs: None
# Restrict to data available at evaluation time; never execute historical orders.
now=datetime.now(timezone.utc)
c=bot.candles("15min",320)
h=bot.candles("1h",220)
if len(c)<100 or len(h)<40:raise RuntimeError("Insufficient recent closed candles")
ef,es,atr=bot.indicators(c)
rows=[]
for i in range(max(85,len(c)-6),len(c)):
    bar=c[i]
    closed_at=bar.t+timedelta(minutes=15)
    if closed_at>now or now-closed_at>timedelta(minutes=75):continue
    # Only completed 1h candles AT this candle close; no future hourly lookahead.
    eligible_h=[v for v in h if v.t+timedelta(hours=1)<=closed_at]
    if len(eligible_h)<40:continue
    with contextlib.redirect_stdout(io.StringIO()):
        sig=bot.signal(c[:i+1],ef[:i+1],es[:i+1],atr[:i+1],eligible_h,i)
    side="NONE";score="";b=False;variant_c=False;strength="";stop="";tp1="";tp2="";tp3=""
    if sig:
        side="LONG" if sig[0]==1 else "SHORT"
        score=sig[8]
        stop,tp1,tp2,tp3=sig[2:6]
        bull,bear,_,_=bot.htf_context_at(eligible_h,bar.t)
        momentum=(ef[i]>ef[i-1] and bar.c>c[i-1].c) if sig[0]==1 else (ef[i]<ef[i-1] and bar.c<c[i-1].c)
        b=bool(momentum and (bull if sig[0]==1 else bear))
        av=atr[i]
        strength=abs(ef[i]-es[i])/av if av and av>0 else 0.0
        variant_c=bool(b and strength>=0.50)
    rows.append(dict(signal_candle_utc=bar.t.isoformat(),closed_at_utc=closed_at.isoformat(),
        assessed_at_utc=now.isoformat(),side=side,score=score,
        b_accepted=int(b),c_accepted=int(variant_c),ema_spread_over_atr=round(strength,4) if strength!="" else "",
        bar_close=bar.c,stop=stop,tp1=tp1,tp2=tp2,tp3=tp3,signal_only_no_orders=1))
if not rows:raise RuntimeError("No fresh completed candles inside 75-minute observation window")
path=P/"gold_forward_bc_snapshot.csv"
with path.open("w",newline="",encoding="utf-8") as o:
    w=csv.DictWriter(o,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
for row in rows:
    print(f"UTC {row['signal_candle_utc']} side={row['side']} score={row['score']} B={row['b_accepted']} C={row['c_accepted']} strength={row['ema_spread_over_atr']}")
print("Forward signal snapshots only; overlapping runs may repeat candle keys. Deduplicate by signal_candle_utc.")
print("No execution/PnL measured; live broker pricing and TP/SL follow-up must be implemented separately.")
