"""Pure Gold V5 paper risk admission rules; no broker, Telegram or I/O."""
from datetime import datetime
from zoneinfo import ZoneInfo
BERLIN=ZoneInfo("Europe/Berlin")
MAX_DAILY_LOSS_R=2.0
MAX_LOSS_STREAK=3
MAX_DRAWDOWN_R=6.0
def risk_gate(rows,as_of):
    forward=[r for r in rows if r.get("cohort")=="FORWARD"]
    closed=sorted((r for r in forward if r.get("status")=="CLOSED_PAPER" and r.get("exit_utc")),key=lambda r:r["exit_utc"])
    active=[r for r in forward if r.get("status") in ("OPEN_PAPER","PENDING_ENTRY")]
    reasons=[]
    if active:reasons.append("EXISTING_POSITION")
    if any(r.get("status")=="UNRESOLVED_DATA_GAP" for r in forward):reasons.append("UNRESOLVED_DATA_GAP")
    localday=as_of.astimezone(BERLIN).date()
    daily=sum(float(r["net_R"]) for r in closed if datetime.fromisoformat(r["exit_utc"]).astimezone(BERLIN).date()==localday)
    if daily<=-MAX_DAILY_LOSS_R:reasons.append("DAILY_LOSS_LIMIT")
    streak=0
    for r in reversed(closed):
        if float(r["net_R"])<0:streak+=1
        else:break
    if streak>=MAX_LOSS_STREAK:reasons.append("LOSS_STREAK_LIMIT")
    eq=peak=dd=0.0
    for r in closed:
        eq+=float(r["net_R"]);peak=max(peak,eq);dd=max(dd,peak-eq)
    if dd>=MAX_DRAWDOWN_R:reasons.append("DRAWDOWN_LIMIT")
    return {"decision":"BLOCK" if reasons else "ALLOW","reasons":reasons,"daily_R":round(daily,5),
            "loss_streak":streak,"max_closed_dd_R":round(dd,5)}
