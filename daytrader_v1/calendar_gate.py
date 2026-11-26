"""Paper-only calendar gate; verified snapshots must come from trusted adapters.
All times are UTC epoch seconds. No network calls or inferred holiday schedule.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

CATEGORIES = frozenset(("FOMC","FED_PRESS","NFP","CPI","PCE","PPI","OTHER_HIGH_USD"))

def evaluate_calendar(now, calendar, market_hours):
    result = dict(news_clear=False, session_clear=False, reasons=[], nearby=[],
                  session=None, session_start=None, mode="PAPER")
    def valid_time(x):
        return type(x) is int and x>0
    if not valid_time(now):
        result["reasons"].append("invalid clock")
        return result
    try:
        if calendar.get("verified") is not True:
            raise ValueError("calendar not verified")
        if not isinstance(calendar.get("source"),str) or not calendar["source"].strip():
            raise ValueError("calendar source missing")
        updated=calendar["verified_at"]
        start,end=calendar["coverage_start"],calendar["coverage_end"]
        if not all(valid_time(t) for t in (updated,start,end)) or not 0<=now-updated<=3600:
            raise ValueError("calendar stale")
        if not start<=now-1800 or not end>=now+1860:
            raise ValueError("news coverage incomplete")
        if not CATEGORIES.issubset(set(calendar["covered_categories"])):
            raise ValueError("calendar categories incomplete")
        events=calendar["events"]
        if not isinstance(events,list):
            raise ValueError("invalid events")
        for event in events:
            stamp=event["timestamp"]
            if not valid_time(stamp) or event["category"] not in CATEGORIES or not isinstance(event["title"],str) or not event["title"].strip():
                raise ValueError("invalid news event")
            if now-1800<=stamp<=now+1860:
                result["nearby"].append(event)
        result["news_clear"]=not result["nearby"]
        if not result["news_clear"]:
            result["reasons"].append("high impact news blackout")
    except (KeyError,TypeError,ValueError,AttributeError) as exc:
        result["reasons"].append("calendar unavailable or invalid")
    try:
        if market_hours.get("verified") is not True or market_hours.get("instrument")!="XAUUSD":
            raise ValueError("unverified broker hours")
        updated=market_hours["verified_at"]
        if not valid_time(updated) or not 0<=now-updated<=3600:
            raise ValueError("stale hours")
        windows=market_hours["windows"]
        if not isinstance(windows,list):
            raise ValueError("invalid windows")
        for w in windows:
            if not valid_time(w["open"]) or not valid_time(w["close"]) or w["open"]>=w["close"]:
                raise ValueError("invalid interval")
        # Research entry windows; broker-specific holiday/early close is mandatory.
        # Last 30 minutes excluded; an independent position manager must flatten.
        for name,tz in (("London","Europe/London"),("New York","America/New_York")):
            local=datetime.fromtimestamp(now,ZoneInfo(tz))
            if local.weekday()>=5 or not 8<=local.hour<16:
                continue
            start=int(local.replace(hour=8,minute=0,second=0,microsecond=0).timestamp())
            end=int(local.replace(hour=16,minute=0,second=0,microsecond=0).timestamp())
            if now+1860>end:
                continue
            matching=[w for w in windows if w["open"]<=now and now+1860<=w["close"]]
            if matching:
                result.update(session_clear=True,session=name,session_start=max(start,matching[0]["open"]))
                break
        if not result["session_clear"]:
            result["reasons"].append("outside permitted session or close approaching")
    except (KeyError,TypeError,ValueError,AttributeError,OverflowError,OSError):
        result["reasons"].append("market hours unavailable or invalid")
    return result
