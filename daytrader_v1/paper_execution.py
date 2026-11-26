"""Quote-driven paper execution only. Never sends broker orders.
Requires independently verified bid/ask snapshots and cost assumptions.
No reconstruction of intrabar fills or assumption that a missed stop filled at its level.
"""
import json
from math import isfinite

def validate_quote(q, now):
    if type(now) is not int or q.get("verified") is not True or q.get("instrument")!="XAUUSD":
        raise ValueError("unverified quote")
    t=q["timestamp"]
    if type(t) is not int or not 0<=now-t<=30:
        raise ValueError("stale or future quote")
    bid,ask=q["bid"],q["ask"]
    if not all(type(x) in (int,float) and isfinite(x) for x in (bid,ask)) or not 0<bid<=ask:
        raise ValueError("invalid bid/ask")
    return t,bid,ask

def valid_cost(x):
    return type(x) in (int,float) and isfinite(x) and x>=0

class PaperExecution:
    def __init__(self,journal):
        self.journal=journal
        self.store=journal.store

    def enter(self,zone_id,quote,now,calendar,risk_context,cost_per_ounce,slippage_per_ounce):
        t,bid,ask=validate_quote(quote,now)
        if not all(valid_cost(x) for x in (cost_per_ounce,slippage_per_ounce)):
            raise ValueError("invalid cost assumptions")
        if calendar.get("news_clear") is not True or calendar.get("session_clear") is not True:
            return "BLOCKED_CALENDAR"
        if calendar.get("as_of")!=now or risk_context.get("as_of")!=now or risk_context.get("verified") is not True:
            return "UNVERIFIED_CONTEXT"
        if risk_context.get("open_positions")!=0 or type(risk_context.get("daily_loss_count")) is not int or not 0<=risk_context["daily_loss_count"]<3:
            return "BLOCKED_RISK"
        equity=risk_context.get("equity_usd")
        used=risk_context.get("daily_planned_risk_usd")
        if not valid_cost(equity) or not valid_cost(used) or equity<=0:
            return "INVALID_RISK"
        with self.store.transaction() as db:
            row=db.execute("SELECT payload FROM signals WHERE zone_id=?",(zone_id,)).fetchone()
        if not row:
            return "NOT_RESERVED"
        d=json.loads(row[0])
        if d.get("mode")!="PAPER" or d.get("signal") not in ("BUY","SELL"):
            return "INVALID_SIGNAL"
        if not d["timestamp"]<=t<=now<=d["valid_until"]:
            return "EXPIRED"
        buy=d["signal"]=="BUY"
        price=ask+slippage_per_ounce if buy else bid-slippage_per_ounce
        # Reject adverse price movement; a later integration may support a
        # separately validated tolerance, but must recompute net risk.
        if (price>d["entry"] if buy else price<d["entry"]):
            return "PRICE_MOVED"
        if not (d["stop"]<price<d["target"] if buy else d["target"]<price<d["stop"]):
            return "INVALID_FILL"
        # Entry slippage is embedded in price. Reserve exit slippage separately.
        unit_risk=abs(price-d["stop"])+cost_per_ounce+slippage_per_ounce
        unit_reward=abs(d["target"]-price)-cost_per_ounce-slippage_per_ounce
        if unit_risk<=0 or unit_reward/unit_risk<2:
            return "CRV_TOO_LOW"
        budget=min(d["planned_risk_usd"],equity*.005,equity*.015-used)
        if budget<=0:
            return "DAILY_LIMIT"
        ounces=min(d["max_ounces"],budget/unit_risk)
        self.journal.enter(zone_id,t,price,ounces,cost_per_ounce+slippage_per_ounce,calendar["session"])
        return "PAPER_FILLED"

    def monitor(self,quote,now,market_hours,cost_per_ounce,slippage_per_ounce):
        t,bid,ask=validate_quote(quote,now)
        if not all(valid_cost(x) for x in (cost_per_ounce,slippage_per_ounce)):
            raise ValueError("invalid cost assumptions")
        with self.store.transaction() as db:
            row=db.execute("""SELECT e.zone_id,e.filled_at,e.ounces,s.payload
                FROM paper_entries e JOIN signals s USING(zone_id)
                LEFT JOIN paper_exits x USING(zone_id) WHERE x.zone_id IS NULL""").fetchone()
        if not row:
            return "NO_POSITION"
        key,filled_at,ounces,payload=row
        if t<=filled_at:
            return "WAIT_NEW_QUOTE"
        d=json.loads(payload)
        buy=d["signal"]=="BUY"
        executable=bid if buy else ask
        price=executable-slippage_per_ounce if buy else executable+slippage_per_ounce
        if price<=0:
            raise ValueError("invalid exit price")
        reason=None
        if (executable<=d["stop"] if buy else executable>=d["stop"]):
            reason="STOP"
        elif (executable>=d["target"] if buy else executable<=d["target"]):
            reason="TARGET"
            # No favorable gap improvement credited on a target.
            price=min(price,d["target"]) if buy else max(price,d["target"])
        # The hours adapter must provide a verified flatten deadline for
        # the current position, not merely the next available session.
        if reason is None:
            if market_hours.get("verified") is not True or type(market_hours.get("flatten_at")) is not int:
                return "HOURS_UNVERIFIED_OPEN_POSITION"
            if t>=market_hours["flatten_at"]:
                reason="SESSION_CLOSE"
        if reason is None:
            return "OPEN"
        self.journal.exit(key,t,price,cost_per_ounce*ounces,reason)
        return reason
