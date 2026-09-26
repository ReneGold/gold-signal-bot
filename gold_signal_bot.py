#!/usr/bin/env python3
from __future__ import annotations
import json, os, time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import requests
from dotenv import load_dotenv

load_dotenv()

# --- Einstellungen wie in TradingView Demo V3.6 ---
FAST=20; SLOW=50; ATR_LEN=14
ATR_BUF=0.25; MAX_RISK_ATR=1.75
TP1_R=0.75; TP2_R=1.50; TP3_R=2.25
MIN_WICK_ATR=0.40; SR_LEN=20; ZONE_ATR=0.35; MIN_PREMOVE_ATR=1.00
TWEEZER_TOL=0.15; BREAKOUT_LEN=10; BREAKOUT_BUF=0.10; BREAKOUT_BODY=0.35
BREAKOUT_STOP_BARS=3; MOM_LEN=5; MOM_BODY=0.35; MINTICK=0.01

API_KEY=os.getenv('TWELVE_DATA_API_KEY','').strip()
TG_TOKEN=os.getenv('TELEGRAM_BOT_TOKEN','').strip()
TG_CHAT=os.getenv('TELEGRAM_CHAT_ID','').strip()
SYMBOL=os.getenv('SYMBOL','XAU/USD')
STATE=Path(os.getenv('STATE_FILE','state.json'))

@dataclass
class Candle:
    t: datetime; o: float; h: float; l: float; c: float

@dataclass
class Plan:
    direction:int; signal_time:str; entry:float; sl:float; tp1:float; tp2:float; tp3:float
    signal_type:str; pattern:str; tp1_hit:bool=False; tp2_hit:bool=False

def send(msg:str):
    print(msg)
    if not TG_TOKEN or not TG_CHAT: return
    r=requests.post(f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',json={'chat_id':TG_CHAT,'text':msg},timeout=20)
    if not r.ok: raise RuntimeError('Telegram: '+r.text)

def load_state():
    if not STATE.exists(): return {'last_processed':None,'plan':None}
    try: return json.loads(STATE.read_text(encoding='utf-8'))
    except Exception: return {'last_processed':None,'plan':None}

def save_state(s):
    STATE.write_text(json.dumps(s,indent=2,ensure_ascii=False),encoding='utf-8')

def candles():
    if not API_KEY: raise RuntimeError('TWELVE_DATA_API_KEY fehlt in .env')
    r=requests.get('https://api.twelvedata.com/time_series',params={
        'symbol':SYMBOL,'interval':'15min','outputsize':250,'timezone':'UTC','format':'JSON','apikey':API_KEY
    },timeout=30); r.raise_for_status(); d=r.json()
    if d.get('status')=='error': raise RuntimeError(d.get('message',str(d)))
    out=[]
    for x in d.get('values',[]):
        t=datetime.fromisoformat(x['datetime']).replace(tzinfo=timezone.utc)
        out.append(Candle(t,float(x['open']),float(x['high']),float(x['low']),float(x['close'])))
    out.sort(key=lambda x:x.t)
    now=datetime.now(timezone.utc)
    return [x for x in out if x.t+timedelta(minutes=15,seconds=20)<=now]

def ema(v,n):
    a=2/(n+1); out=[]; e=v[0]
    for x in v:
        e=a*x+(1-a)*e; out.append(e)
    return out

def rma(v,n):
    out=[None]*len(v)
    if len(v)<n:return out
    p=sum(v[:n])/n; out[n-1]=p
    for i in range(n,len(v)):
        p=(v[i]+(n-1)*p)/n; out[i]=p
    return out

def indicators(c):
    cl=[x.c for x in c]; ef=ema(cl,FAST); es=ema(cl,SLOW); tr=[]
    for i,x in enumerate(c):
        tr.append(x.h-x.l if i==0 else max(x.h-x.l,abs(x.h-c[i-1].c),abs(x.l-c[i-1].c)))
    return ef,es,rma(tr,ATR_LEN)

def signal(c,ef,es,atr,i):
    if i<70 or atr[i] is None:return None
    A=atr
    body=lambda j:max(abs(c[j].c-c[j].o),MINTICK)
    b1,b2,b3=body(i-1),body(i-2),body(i-3)
    lw=min(c[i-1].o,c[i-1].c)-c[i-1].l; uw=c[i-1].h-max(c[i-1].o,c[i-1].c)
    hammer=lw>=2*b1 and uw<=b1 and lw>=A[i-1]*MIN_WICK_ATR
    shooting=uw>=2*b1 and lw<=b1 and uw>=A[i-1]*MIN_WICK_ATR
    bull_eng=c[i-2].c<c[i-2].o and c[i-1].c>c[i-1].o and c[i-1].o<=c[i-2].c and c[i-1].c>=c[i-2].o
    bear_eng=c[i-2].c>c[i-2].o and c[i-1].c<c[i-1].o and c[i-1].o>=c[i-2].c and c[i-1].c<=c[i-2].o
    morning=c[i-3].c<c[i-3].o and b3>=A[i-3]*.45 and b2<=b3*.55 and b2<=A[i-2]*.35 and c[i-1].c>c[i-1].o and b1>=A[i-1]*.30 and c[i-1].c>=(c[i-3].o+c[i-3].c)/2
    evening=c[i-3].c>c[i-3].o and b3>=A[i-3]*.45 and b2<=b3*.55 and b2<=A[i-2]*.35 and c[i-1].c<c[i-1].o and b1>=A[i-1]*.30 and c[i-1].c<=(c[i-3].o+c[i-3].c)/2
    tw_bot=c[i-2].c<c[i-2].o and c[i-1].c>c[i-1].o and abs(c[i-1].l-c[i-2].l)<=A[i-1]*TWEEZER_TOL and c[i-1].c>=(c[i-2].o+c[i-2].c)/2
    tw_top=c[i-2].c>c[i-2].o and c[i-1].c<c[i-1].o and abs(c[i-1].h-c[i-2].h)<=A[i-1]*TWEEZER_TOL and c[i-1].c<=(c[i-2].o+c[i-2].c)/2
    bull=hammer or bull_eng or morning or tw_bot; bear=shooting or bear_eng or evening or tw_top
    bull_name='MORNING STAR' if morning else 'TWEEZER BOTTOM' if tw_bot else 'BULL ENGULF' if bull_eng else 'HAMMER' if hammer else 'WENDE'
    bear_name='EVENING STAR' if evening else 'TWEEZER TOP' if tw_top else 'BEAR ENGULF' if bear_eng else 'SHOOTING STAR' if shooting else 'WENDE'
    patt_low=min(c[i-1].l,c[i-2].l,c[i-3].l); patt_high=max(c[i-1].h,c[i-2].h,c[i-3].h)
    s0=i-4-SR_LEN+1; support=min(x.l for x in c[s0:i-3]); resist=max(x.h for x in c[s0:i-3])
    near_sup=patt_low<=support+A[i-1]*ZONE_ATR; near_res=patt_high>=resist-A[i-1]*ZONE_ATR
    near_ema=abs(c[i-1].c-es[i-1])<=A[i-1]*ZONE_ATR
    prev_down=c[i-6].c-c[i-1].c>=A[i-1]*MIN_PREMOVE_ATR; prev_up=c[i-1].c-c[i-6].c>=A[i-1]*MIN_PREMOVE_ATR
    long_ctx=near_sup or (near_ema and prev_down) or (prev_down and (morning or tw_bot))
    short_ctx=near_res or (near_ema and prev_up) or (prev_up and (evening or tw_top))
    up=ef[i]>es[i] and c[i].c>ef[i]; down=ef[i]<es[i] and c[i].c<ef[i]
    was_down=ef[i-1]<ef[i-3] and c[i-1].c<es[i-1]; was_up=ef[i-1]>ef[i-3] and c[i-1].c>es[i-1]
    lc=bull and c[i].c>c[i-1].h and c[i].c>c[i].o; sc=bear and c[i].c<c[i-1].l and c[i].c<c[i].o
    lt=lc and up; st=sc and down; le=lc and was_down and long_ctx and not lt; se=sc and was_up and short_ctx and not st
    bh=max(x.h for x in c[i-BREAKOUT_LEN:i]); bl=min(x.l for x in c[i-BREAKOUT_LEN:i]); cur_body=abs(c[i].c-c[i].o)
    pbh=max(x.h for x in c[i-1-BREAKOUT_LEN:i-1]); pbl=min(x.l for x in c[i-1-BREAKOUT_LEN:i-1])
    lb=up and ef[i]>ef[i-1] and c[i].c>c[i].o and cur_body>=A[i]*BREAKOUT_BODY and c[i].c>bh+A[i]*BREAKOUT_BUF and c[i-1].c<=pbh+A[i-1]*BREAKOUT_BUF
    sb=down and ef[i]<ef[i-1] and c[i].c<c[i].o and cur_body>=A[i]*BREAKOUT_BODY and c[i].c<bl-A[i]*BREAKOUT_BUF and c[i-1].c>=pbl-A[i-1]*BREAKOUT_BUF
    mh=max(x.h for x in c[i-MOM_LEN:i]); ml=min(x.l for x in c[i-MOM_LEN:i])
    lm=(not le and ef[i]<=es[i] and ef[i]>ef[i-1] and ef[i-1]>=ef[i-2] and (es[i]-ef[i])<(es[i-2]-ef[i-2]) and c[i].c>es[i] and c[i].c>mh and c[i].c>c[i].o and cur_body>=A[i]*MOM_BODY)
    sm=(not se and ef[i]>=es[i] and ef[i]<ef[i-1] and ef[i-1]<=ef[i-2] and (ef[i]-es[i])<(ef[i-2]-es[i-2]) and c[i].c<es[i] and c[i].c<ml and c[i].c<c[i].o and cur_body>=A[i]*MOM_BODY)
    long_cand=lt or le or lb or lm; short_cand=st or se or sb or sm
    lstop_turn=min(c[i].l,c[i-1].l)-A[i]*ATR_BUF; sstop_turn=max(c[i].h,c[i-1].h)+A[i]*ATR_BUF
    lstop_br=min(min(x.l for x in c[i-BREAKOUT_STOP_BARS+1:i+1]),bh)-A[i]*ATR_BUF
    sstop_br=max(max(x.h for x in c[i-BREAKOUT_STOP_BARS+1:i+1]),bl)+A[i]*ATR_BUF
    lstop_m=min(x.l for x in c[i-2:i+1])-A[i]*ATR_BUF; sstop_m=max(x.h for x in c[i-2:i+1])+A[i]*ATR_BUF
    if long_cand:
        sl=lstop_m if lm else lstop_br if lb else lstop_turn; risk=c[i].c-sl
        if MINTICK<risk<=A[i]*MAX_RISK_ATR:
            typ='MOMENTUM-WENDE' if lm else 'AUSBRUCH' if lb else ('FRUEH / '+bull_name) if le else ('TRENDFOLGE / '+bull_name)
            pat='Momentum-Wende' if lm else 'Ausbruch' if lb else bull_name
            return 1,c[i].c,sl,c[i].c+TP1_R*risk,c[i].c+TP2_R*risk,c[i].c+TP3_R*risk,typ,pat
    if short_cand:
        sl=sstop_m if sm else sstop_br if sb else sstop_turn; risk=sl-c[i].c
        if MINTICK<risk<=A[i]*MAX_RISK_ATR:
            typ='MOMENTUM-WENDE' if sm else 'AUSBRUCH' if sb else ('FRUEH / '+bear_name) if se else ('TRENDFOLGE / '+bear_name)
            pat='Momentum-Wende' if sm else 'Ausbruch' if sb else bear_name
            return -1,c[i].c,sl,c[i].c-TP1_R*risk,c[i].c-TP2_R*risk,c[i].c-TP3_R*risk,typ,pat
    return None

def fmt(x):return f'{x:.2f}'

def new_plan_message(p:Plan):
    side='KAUF / LONG' if p.direction==1 else 'VERKAUF / SHORT'; icon='🟢' if p.direction==1 else '🔴'
    return (f'{icon} GOLD DEMO – {side}\nSignal: {p.signal_type}\nMuster: {p.pattern}\n'
            f'Einstieg: {fmt(p.entry)}\nStop-Loss: {fmt(p.sl)}\nTP1: {fmt(p.tp1)}\nTP2: {fmt(p.tp2)}\nTP3: {fmt(p.tp3)}\n'
            f'Zeitrahmen: 15 Minuten\nKerze: {p.signal_time}\nHinweis: Demo-Signal, keine Garantie.')

def process(c,ef,es,atr,i,state):
    just_finished=False
    if state.get('plan'):
        p=Plan(**state['plan']); b=c[i]
        protective=p.tp1 if p.tp2_hit else p.entry if p.tp1_hit else p.sl
        stop=b.l<=protective if p.direction==1 else b.h>=protective
        h3=b.h>=p.tp3 if p.direction==1 else b.l<=p.tp3
        h2=b.h>=p.tp2 if p.direction==1 else b.l<=p.tp2
        h1=b.h>=p.tp1 if p.direction==1 else b.l<=p.tp1
        if stop:
            send(f'🛑 GOLD DEMO – STOP\nSchutz-Stop: {fmt(protective)}\nPlan beendet.'); state['plan']=None; just_finished=True
        elif h3:
            send(f'✅ GOLD DEMO – TP3 erreicht\nTP3: {fmt(p.tp3)}\nPlan abgeschlossen.'); state['plan']=None; just_finished=True
        else:
            if h2 and not p.tp2_hit:
                p.tp1_hit=True; p.tp2_hit=True; send(f'✅ GOLD DEMO – TP2 erreicht\nTP2: {fmt(p.tp2)}\nSchutz-Stop ab naechster Kerze auf TP1: {fmt(p.tp1)}')
            elif h1 and not p.tp1_hit:
                p.tp1_hit=True; send(f'✅ GOLD DEMO – TP1 erreicht\nTP1: {fmt(p.tp1)}\nSchutz-Stop ab naechster Kerze auf Einstieg: {fmt(p.entry)}')
            state['plan']=asdict(p)
    if state.get('plan') is None and not just_finished:
        s=signal(c,ef,es,atr,i)
        if s:
            p=Plan(s[0],c[i].t.isoformat(),s[1],s[2],s[3],s[4],s[5],s[6],s[7]); state['plan']=asdict(p); send(new_plan_message(p))

def run_once():
    c=candles()
    if len(c)<80: raise RuntimeError(f'Zu wenige Kerzen: {len(c)}')
    ef,es,atr=indicators(c); state=load_state(); last=state.get('last_processed')
    idx=[len(c)-1] if not last else [i for i,x in enumerate(c) if x.t.isoformat()>last]
    for i in idx:
        process(c,ef,es,atr,i,state); state['last_processed']=c[i].t.isoformat(); save_state(state)
    print(datetime.now().isoformat(timespec='seconds'),'-',len(idx),'neue Kerze(n)')

def wait_seconds():
    now=datetime.now(timezone.utc); mins=15-(now.minute%15)
    nxt=now.replace(second=0,microsecond=0)+timedelta(minutes=mins,seconds=25)
    return max(20,int((nxt-now).total_seconds()))

def main():
    print('Gold Signal Bot V1 gestartet – keine automatischen Orders.')
    while True:
        try: run_once()
        except KeyboardInterrupt: break
        except Exception as e:
            print('FEHLER:',e)
            try: send('⚠️ Gold Signal Bot Fehler: '+str(e))
            except Exception: pass
        time.sleep(wait_seconds())

if __name__=='__main__': main()
