"""Research-only staged exit planner for XAU/USD. No broker orders.
Units are R multiples of original per-ounce risk; transaction costs excluded.
Default targets 0.75R, 1.50R, 2.25R, slices 30/30/40 percent.
After TP1, stop moves to breakeven; after TP2, stop moves to TP1.
A completed OHLC bar may cross both stop and target. Assume stop FIRST.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class Plan:
    entry: float
    stop: float
    side: int
    target_r: tuple=(0.75,1.5,2.25)
    portions: tuple=(0.30,0.30,0.40)
    def __post_init__(self):
        if self.side not in (-1,1) or not all(isfinite(v) for v in (self.entry,self.stop)):
            raise ValueError("Invalid prices/side")
        if self.entry<=0 or self.stop<=0 or (self.entry-self.stop)*self.side<=0:
            raise ValueError("Invalid protective stop")
        if len(self.target_r)!=3 or len(self.portions)!=3 or any(x<=0 or not isfinite(x) for x in (*self.target_r,*self.portions)):
            raise ValueError("Invalid targets/portions")
        if tuple(sorted(self.target_r))!=tuple(self.target_r) or len(set(self.target_r))!=3:
            raise ValueError("Targets must rise strictly")
        if abs(sum(self.portions)-1)>1e-8:raise ValueError("Portions must total 100%")
    @property
    def risk(self):return (self.entry-self.stop)*self.side
    @property
    def targets(self):return tuple(self.entry+self.side*self.risk*x for x in self.target_r)

def new_position(plan):
    return {"stage":0,"remaining":1.0,"gross_R":0.0,"closed":False,"events":[]}

def on_bar(plan,state,*,open_price,high,low,close):
    """Mutate one paper position once per bar, returning it.
    Stage 0: initial stop. Stage 1: breakeven. Stage 2: TP1 stop.
    For a gap beyond stop, fill at open (potentially worse).
    Multiple TPs in one bar are allowed only if the protective stop was not hit.
    """
    if state["closed"]:return state
    if not all(isfinite(x) for x in (open_price,high,low,close)) or low>high or not(low<=open_price<=high and low<=close<=high):
        raise ValueError("Invalid OHLC")
    stage=state["stage"]
    protective=(plan.stop,plan.entry,plan.targets[0])[stage]
    stop_hit=(low<=protective if plan.side==1 else high>=protective)
    gap=(open_price<=protective if plan.side==1 else open_price>=protective)
    if stop_hit:
        px=open_price if gap else protective
        state["gross_R"]+=state["remaining"]*(px-plan.entry)*plan.side/plan.risk
        state["events"].append("STOP")
        state["remaining"]=0.0
        state["closed"]=True
        return state
    for ix in range(stage,3):
        tp=plan.targets[ix]
        hit=(high>=tp if plan.side==1 else low<=tp)
        if not hit:break
        portion=min(plan.portions[ix],state["remaining"])
        state["gross_R"]+=portion*plan.target_r[ix]
        state["remaining"]=round(state["remaining"]-portion,10)
        state["events"].append("TP"+str(ix+1))
        state["stage"]=ix+1
    if state["stage"]==3:
        state["closed"]=True
    return state
