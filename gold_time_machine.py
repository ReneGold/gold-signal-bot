"""Gold Time Machine: historical analog replay only, no prediction or orders.

Uses only analog signal times whose *entire* future replay window ended
before the current signal was observed. Outcome assumes entry at next open,
fixed stop/target, conservative stop-first ordering for same-bar collisions.
Research output is descriptive, not calibrated odds.
"""
from dataclasses import dataclass
from math import isfinite
from statistics import median

@dataclass(frozen=True)
class Bar:
    open: float
    high: float
    low: float
    close: float

def features(bars,i):
    if i<3:return None
    last=bars[i]
    prev=bars[i-1]
    scale=max(last.high-last.low,1e-8)
    return ((last.close-last.open)/scale,
            (last.close-prev.close)/max(prev.close,1e-8),
            (last.high-last.low)/max(last.close,1e-8))

def replay(bars,signal_i,side,stop_distance,target_r=2.0,horizon=12,cost_per_oz=0.5):
    if signal_i+1>=len(bars) or signal_i+1+horizon>len(bars):
        raise ValueError("Complete forward replay candles required")
    entry=bars[signal_i+1].open
    sl=entry-side*stop_distance
    tp=entry+side*stop_distance*target_r
    if sl<=0:raise ValueError("Invalid stop")
    for k in range(signal_i+1,signal_i+1+horizon):
        bar=bars[k]
        stop_hit=(bar.low<=sl if side==1 else bar.high>=sl)
        tp_hit=(bar.high>=tp if side==1 else bar.low<=tp)
        gap=(bar.open<=sl if side==1 else bar.open>=sl)
        if stop_hit:
            exit_price=bar.open if gap else sl
            return ((exit_price-entry)*side-cost_per_oz)/stop_distance,"STOP"
        if tp_hit:return (target_r*stop_distance-cost_per_oz)/stop_distance,"TARGET"
    final=bars[signal_i+horizon].close
    return ((final-entry)*side-cost_per_oz)/stop_distance,"TIMEOUT"

def analyze(bars,signal_i,side,stop_distance,target_r=2.0,horizon=12,
            lookback=1200,max_examples=100,cost_per_oz=0.5):
    if side not in (-1,1) or stop_distance<=0 or horizon<1 or lookback<1 or max_examples<1:
        raise ValueError("Invalid replay parameters")
    if signal_i<4 or signal_i>=len(bars):raise ValueError("Invalid signal index")
    if not all(isfinite(v) for b in bars[:signal_i+1] for v in (b.open,b.high,b.low,b.close)):
        raise ValueError("Invalid OHLC data")
    target=features(bars,signal_i)
    # Exclude current signal and any analog whose horizon is not fully
    # known by current signal close (no overlapping future/lookahead).
    upper=signal_i-horizon
    candidates=[]
    for j in range(max(3,signal_i-lookback),upper):
        f=features(bars,j)
        if not f:continue
        # Similar body direction preferred and relative volatility weighted.
        if f[0]*target[0]<0:continue
        dist=abs(f[0]-target[0])+100*abs(f[1]-target[1])+100*abs(f[2]-target[2])
        candidates.append((dist,j))
    selected=sorted(candidates)[:max_examples]
    if not selected:
        return dict(sample_size=0,mean_net_r=None,median_net_r=None,stop_count=0,
                    target_count=0,timeout_count=0,warning="No prior completed comparable windows")
    results=[replay(bars,j,side,stop_distance,target_r,horizon,cost_per_oz) for _,j in selected]
    rs=[r for r,_ in results]
    return dict(sample_size=len(results),mean_net_r=round(sum(rs)/len(rs),4),
                median_net_r=round(median(rs),4),
                stop_count=sum(o=="STOP" for _,o in results),
                target_count=sum(o=="TARGET" for _,o in results),
                timeout_count=sum(o=="TIMEOUT" for _,o in results),
                warning="Uncalibrated historical analogs; overlapping analog windows and regime changes; not predictive odds")
