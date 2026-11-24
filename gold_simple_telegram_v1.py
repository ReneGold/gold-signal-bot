#!/usr/bin/env python3
"""Gold SIMPLE V1: standalone, PAPER ONLY. Does not consume TradingView alerts.
Same EMA9/21/50 close-cross signal and ATR14 1.5x stop, 2R take profit.
One Twelve Data request; message to Telegram only with explicit --send-paper.
No broker connection, no order placement.
"""
import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

INTERVAL_MINUTES=15

def ema(series, n):
    if not series:return []
    k=2/(n+1)
    out=[series[0]]
    for v in series[1:]:out.append(k*v+(1-k)*out[-1])
    return out

def rma(series,n):
    out=[None]*len(series)
    if len(series)<n:return out
    out[n-1]=sum(series[:n])/n
    for i in range(n,len(series)):out[i]=(series[i]+(n-1)*out[i-1])/n
    return out

def evaluate(bars):
    """Ascending UTC bars, last bar fully closed; no forward-looking logic."""
    if len(bars)<60:return None
    t=[x["time"] for x in bars]
    if any(y-x!=timedelta(minutes=15) for x,y in zip(t[-51:],t[-50:])):
        return None   # never synthesize missing candles
    c=[x["close"] for x in bars]
    f,s,z=ema(c,9),ema(c,21),ema(c,50)
    tr=[]
    for i,b in enumerate(bars):
        prev=c[i-1] if i else c[0]
        tr.append(max(b["high"]-b["low"],abs(b["high"]-prev),abs(b["low"]-prev)))
    atr=rma(tr,14)[-1]
    if atr is None or atr<=0:return None
    buy=f[-2]<=s[-2] and f[-1]>s[-1] and c[-1]>z[-1]
    sell=f[-2]>=s[-2] and f[-1]<s[-1] and c[-1]<z[-1]
    if not (buy or sell):return None
    direction=1 if buy else -1
    entry=round(c[-1],2)
    stop=round(entry-direction*1.5*atr,2)
    target=round(entry+direction*3.0*atr,2)
    return dict(side="KAUFEN / LONG" if buy else "VERKAUFEN / SHORT",
                signal_close=(bars[-1]["time"]+timedelta(minutes=15)).isoformat(),
                entry=entry,stop=stop,target=target)

def closed_bars(payload,now):
    if payload.get("status")=="error":raise RuntimeError("Feed error: "+str(payload.get("message","unknown")))
    result=[]
    for v in payload.get("values",[]):
        t=datetime.fromisoformat(v["datetime"]).replace(tzinfo=timezone.utc)
        b={"time":t,**{k:float(v[k]) for k in ("open","high","low","close")}}
        if b["low"]>min(b["open"],b["close"]) or b["high"]<max(b["open"],b["close"]):
            raise ValueError("invalid OHLC")
        if t+timedelta(minutes=15,seconds=20)<=now:result.append(b)
    result.sort(key=lambda b:b["time"])
    if any(x["time"]>=y["time"] for x,y in zip(result,result[1:])):raise ValueError("duplicate bars")
    return result

def download(api_key):
    query=urllib.parse.urlencode({"symbol":"XAU/USD","interval":"15min","outputsize":300,
                                 "timezone":"UTC","apikey":api_key})
    with urllib.request.urlopen("https://api.twelvedata.com/time_series?"+query,timeout=20) as r:
        return json.load(r)

def telegram(message,token,chat):
    data=urllib.parse.urlencode({"chat_id":chat,"text":message}).encode()
    req=urllib.request.Request("https://api.telegram.org/bot"+token+"/sendMessage",data=data)
    with urllib.request.urlopen(req,timeout=20) as r:
        result=json.load(r)
    if not result.get("ok"):raise RuntimeError("Telegram did not accept paper test")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--send-paper",action="store_true",help="Only after manual approval; send once if fresh qualifying signal")
    p.add_argument("--test-telegram",action="store_true",help="Send clearly marked technical connectivity test only")
    args=p.parse_args()
    if args.test_telegram:
        token=os.getenv("TELEGRAM_BOT_TOKEN","")
        chat=os.getenv("TELEGRAM_CHAT_ID","")
        if not token or not chat:raise RuntimeError("Missing Telegram secrets")
        telegram("GOLD SIMPLE V1: Telegram-Verbindungstest OK. KEIN HANDELSSIGNAL.",token,chat)
        print("Telegram test accepted")
        return
    key=os.getenv("TWELVE_DATA_API_KEY","")
    if not key:raise RuntimeError("Missing TWELVE_DATA_API_KEY")
    now=datetime.now(timezone.utc)
    bars=closed_bars(download(key),now)
    signal=evaluate(bars)
    if signal is None:
        print("NO_SIGNAL (or missing 15m candles)")
        return
    # Only a newly finished bar should trigger delivery. Scheduled job drift is NOT backfilled.
    close=datetime.fromisoformat(signal["signal_close"])
    if now-close>timedelta(minutes=5):
        print("STALE_SIGNAL, not sent")
        return
    msg=(f"GOLD SIMPLE V1 | TEST / PAPER – KEINE ORDER\\n{signal['side']}\\n"
         f"Einstieg ca. {signal['entry']:.2f}\\nStop-Loss {signal['stop']:.2f}\\n"
         f"Take-Profit {signal['target']:.2f}\\nZeit (UTC) {signal['signal_close']}")
    print(msg)
    if args.send_paper:
        token=os.getenv("TELEGRAM_BOT_TOKEN","")
        chat=os.getenv("TELEGRAM_CHAT_ID","")
        if not token or not chat:raise RuntimeError("Missing Telegram secrets")
        telegram(msg,token,chat)

if __name__=="__main__":main()
