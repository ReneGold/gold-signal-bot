#!/usr/bin/env python3
"""Gold SIMPLE V1: ONE PAPER signal, EMA9/21/50 and ATR14.
Independent of TradingView Basic: Twelve Data candles => Telegram.
No brokerage, no order placement. No auto tuning or fake candle filling.
"""
import argparse, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from gold_simple_telegram_v1 import closed_bars, download, ema, rma, telegram

STEP=timedelta(minutes=15)
STATE=Path("gold_simple_v1_sent_state.json")

def latest_signal(bars):
    """Approximate Pine SIMPLE's state machine using only available closed bars.
    For parity use close-entry and stop-first OHLC approximations. Different
    provider OHLC/history can produce different TradingView labels.
    """
    if len(bars)<80:return None,"INSUFFICIENT_BARS"
    if any(b["time"]+STEP!=n["time"] for b,n in zip(bars[-51:],bars[-50:])):
        return None,"RECENT_DATA_GAP"
    close=[b["close"] for b in bars]
    fast,slow,trend=ema(close,9),ema(close,21),ema(close,50)
    tr=[]
    for i,b in enumerate(bars):
        previous=close[i-1] if i else close[0]
        tr.append(max(b["high"]-b["low"],abs(b["high"]-previous),abs(b["low"]-previous)))
    atr=rma(tr,14)
    direction=0
    stop=target=0.0
    entry_bar=-1
    signal=None
    for i in range(51,len(bars)):
        b=bars[i]
        # Do not use historic discontinuities for a new entry.
        if b["time"]-bars[i-1]["time"]!=STEP:
            direction=0
            signal=None
            continue
        closed_this_bar=False
        if direction and i>entry_bar:
            if (b["low"]<=stop if direction==1 else b["high"]>=stop) or (b["high"]>=target if direction==1 else b["low"]<=target):
                direction=0
                closed_this_bar=True
        if direction or closed_this_bar or atr[i] is None:
            continue
        up=fast[i-1]<=slow[i-1] and fast[i]>slow[i] and close[i]>trend[i]
        down=fast[i-1]>=slow[i-1] and fast[i]<slow[i] and close[i]<trend[i]
        if not (up or down):continue
        direction=1 if up else -1
        entry=round(close[i],2)
        stop=round(entry-direction*1.5*atr[i],2)
        target=round(entry+direction*3.0*atr[i],2)
        entry_bar=i
        signal={"signal_close":(b["time"]+STEP).isoformat(),
                "side":"KAUFEN / LONG" if up else "VERKAUFEN / SHORT",
                "entry":entry,"stop":stop,"target":target}
    # Only CURRENT candle may generate a fresh signal.
    if signal and entry_bar==len(bars)-1:return signal,"NEW_SIGNAL"
    return None,"NO_NEW_SIGNAL"

def load_state(path):
    if not path.exists():return {}
    obj=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj,dict):raise ValueError("state must be object")
    return obj

def process(bars, now, state, send_callback, max_age=timedelta(minutes=11)):
    signal,reason=latest_signal(bars)
    if signal is None:return reason,state
    finished=datetime.fromisoformat(signal["signal_close"])
    age=now-finished
    if age<timedelta(seconds=20) or age>max_age:return "STALE_OR_EARLY",state
    if state.get("last_sent_signal_close")==signal["signal_close"]:return "DUPLICATE_BLOCKED",state
    message=(f"GOLD SIMPLE V1 | PAPER-SIGNAL (KEINE ORDER)\n"
             f"{signal['side']} | XAUUSD 15m\n"
             f"Einstieg ca.: {signal['entry']:.2f}\n"
             f"Stop-Loss: {signal['stop']:.2f}\n"
             f"Take-Profit: {signal['target']:.2f}\n"
             f"Kerzenschluss UTC: {signal['signal_close']}\n"
             "Indikative Kurse; Brokerpreis kann abweichen. Nicht auf Gewinn geprüft.")
    send_callback(message)
    return "PAPER_SENT",{"last_sent_signal_close":signal["signal_close"],
                         "side":signal["side"],"sent_utc":now.isoformat()}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--send-paper",action="store_true")
    parser.add_argument("--state",type=Path,default=STATE)
    args=parser.parse_args()
    key=os.getenv("TWELVE_DATA_API_KEY","")
    if not key:raise RuntimeError("Missing TWELVE_DATA_API_KEY")
    now=datetime.now(timezone.utc)
    bars=closed_bars(download(key),now)
    state=load_state(args.state)
    def deliver(message):
        print(message)
        if args.send_paper:
            token=os.getenv("TELEGRAM_BOT_TOKEN","")
            chat=os.getenv("TELEGRAM_CHAT_ID","")
            if not token or not chat:raise RuntimeError("Missing Telegram credentials")
            telegram(message,token,chat)
    result,updated=process(bars,now,state,deliver)
    print("STATUS="+result)
    if result=="PAPER_SENT" and args.send_paper:
        args.state.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

if __name__=="__main__":main()
