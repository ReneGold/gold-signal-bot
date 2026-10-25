"""Research-only pre-trade risk gate for XAU/USD; does not place orders.
All currency values must be in a consistent account currency, including contract value.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class RiskPolicy:
    max_trade_risk_pct: float = 0.5
    max_daily_loss_pct: float = 2.0
    max_open_positions: int = 1
    min_reward_risk: float = 1.5

def check_trade(*, equity, day_realized_pnl, entry, stop, target,
                quantity_oz, open_positions, policy=RiskPolicy()):
    reasons=[]
    nums=(equity,day_realized_pnl,entry,stop,target,quantity_oz)
    if not all(isinstance(v,(int,float)) and isfinite(v) for v in nums):
        return {"approved":False,"reasons":["Non-finite or missing numeric data"]}
    if equity<=0 or quantity_oz<=0 or entry<=0 or stop<=0 or target<=0:
        reasons.append("Equity, size and prices must be positive")
    if any((policy.max_trade_risk_pct<=0,policy.max_daily_loss_pct<=0,
            policy.max_open_positions<1,policy.min_reward_risk<=0)):
        reasons.append("Invalid policy")
    if open_positions<0 or open_positions>=policy.max_open_positions:
        reasons.append("Open-position limit reached")
    direction=1 if target>entry else -1 if target<entry else 0
    risk_per_oz=(entry-stop)*direction
    reward_per_oz=(target-entry)*direction
    if direction==0 or risk_per_oz<=0 or reward_per_oz<=0:
        reasons.append("Invalid direction, stop or target")
    if equity>0 and quantity_oz>0 and risk_per_oz>0:
        estimated_loss=risk_per_oz*quantity_oz
        if estimated_loss>equity*policy.max_trade_risk_pct/100:
            reasons.append("Position exceeds per-trade risk")
    else:
        estimated_loss=None
    if equity>0 and day_realized_pnl<=-equity*policy.max_daily_loss_pct/100:
        reasons.append("Daily loss limit reached")
    rr=reward_per_oz/risk_per_oz if risk_per_oz>0 else None
    if rr is not None and rr<policy.min_reward_risk:
        reasons.append("Reward/risk below minimum")
    return {"approved":not reasons,"reasons":reasons,
            "estimated_stop_loss_account_ccy":estimated_loss,"reward_risk":rr}
