#!/usr/bin/env python3
"""V3.9.6 conservative OHLC execution test; no orders, no partial exits."""
import csv,importlib.util,io,contextlib,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
P=Path(__file__).resolve().parent
source=P/'gold_signal_bot_v3_9_5_diagnose (2).py'
spec=importlib.util.spec_from_file_location('bot_long',source)
bot=importlib.util.module_from_spec(spec);sys.modules[spec.name]=bot;spec.loader.exec_module(bot)
bot.send=lambda *args:None
bot.save_state=lambda *args:None
def load(interval):
    filename=P/'gold_historical_data'/f'xauusd_{interval}_20260801_20261024.csv'
    out=[]
    with filename.open(newline='') as f:
        for row in csv.DictReader(f):
            t=datetime.fromisoformat(row['datetime_utc'])
            if t.weekday()>=5:continue
            out.append(bot.Candle(t,*(float(row[k]) for k in ('open','high','low','close'))))
    return out
c=load('15min');htf=load('1h')
if len(c)<4000 or len(htf)<1000:raise RuntimeError(f'Incomplete series 15m={len(c)} 1h={len(htf)}')
ef,es,atr=bot.indicators(c)
trades=[];fee=0.50
for threshold in (60,65,70):
    bot.MIN_SCORE=threshold
    pos=None
    for i in range(85,len(c)-1):
        bar=c[i]
        if pos is not None:
            sign,entry,sl,tp1,tp2,tp3,opened,score,t1,t2=pos
            protect=tp1 if t2 else entry if t1 else sl
            stopped=bar.l<=protect if sign==1 else bar.h>=protect
            third=bar.h>=tp3 if sign==1 else bar.l<=tp3
            # Opening gap beyond protective stop: fill at bar open, never at a better stop level.
            gap_stop=(bar.o<=protect if sign==1 else bar.o>=protect)
            # If both TP3 and stop are touched within one candle, assume stop first.
            ambiguous=stopped and third
            second=bar.h>=tp2 if sign==1 else bar.l<=tp2
            first=bar.h>=tp1 if sign==1 else bar.l<=tp1
            if stopped or third:
                price=(bar.o if gap_stop else protect) if stopped else tp3
                risk=abs(entry-sl)
                net=((price-entry)*sign-fee)/risk
                trades.append(dict(score_min=threshold,opened=opened,closed=bar.t.isoformat(),side='LONG' if sign==1 else 'SHORT',signal_score=score,entry=entry,sl=sl,tp1=tp1,tp2=tp2,tp3=tp3,exit=price,outcome=('GAP_STOP' if gap_stop else 'STOP') if stopped else 'TP3',net_R=round(net,5)))
                pos=None
                continue
            if second:t1=t2=True
            elif first:t1=True
            pos=(sign,entry,sl,tp1,tp2,tp3,opened,score,t1,t2)
            continue
        if bar.t.weekday()==4 and bar.t.hour>=20:continue
        if bar.t.hour<1:continue
        if c[i+1].t-bar.t!=timedelta(minutes=15):continue
        with contextlib.redirect_stdout(io.StringIO()):
            s=bot.signal(c,ef,es,atr,htf,i)
        if not s:continue
        sign=s[0];entry=c[i+1].o;sl=s[2];risk=(entry-sl)*sign
        if risk<=0:continue
        tp1=entry+sign*bot.TP1_R*risk;tp2=entry+sign*bot.TP2_R*risk;tp3=entry+sign*bot.TP3_R*risk
        pos=(sign,entry,sl,tp1,tp2,tp3,c[i+1].t.isoformat(),s[8],False,False)
    if pos:print('OPEN at end excluded',threshold,pos[6],pos[7],flush=True)
    print('Completed threshold',threshold,flush=True)
fields=['score_min','opened','closed','side','signal_score','entry','sl','tp1','tp2','tp3','exit','outcome','net_R']
with (P/'gold_long_backtest_trades.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(trades)
for threshold in (60,65,70):
    ts=[r for r in trades if r['score_min']==threshold];v=[r['net_R'] for r in ts]
    if not v:print('Score',threshold,'no closed trades');continue
    wins=sum(x for x in v if x>0);losses=-sum(x for x in v if x<0)
    balance=peak=dd=0;streak=maxstreak=0
    for x in v:
        balance+=x;peak=max(peak,balance);dd=max(dd,peak-balance)
        streak=streak+1 if x<0 else 0;maxstreak=max(maxstreak,streak)
    print(f'Score {threshold}: trades={len(v)} wins={sum(x>0 for x in v)} net_R={sum(v):.3f} PF={wins/losses if losses else float("inf"):.2f} max_closed_drawdown_R={dd:.2f} max_loss_streak={maxstreak}')
print('LIMITS V3.9.6: no partial exits; modeled roundtrip cost 0.5 USD/oz; intrabar stop first; gap-stop at open; same-bar TP1/TP2 do not move stop until next candle; trading sessions and broker execution not validated.')
