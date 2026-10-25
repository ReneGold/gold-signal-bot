"""Free Finance Calendar economic event provider for V4 research (no paid key).
Source: https://www.financecalendar.com/api/ (attribution required).
Research-only, fail-closed. An empty/incomplete feed is NEVER verified safe.
"""
import json,urllib.request,urllib.parse
from datetime import datetime,timedelta,timezone
from gold_news_volatility_filter import Event

BASE="https://www.financecalendar.com/wp-json/fc/v1/calendar"
ATTRIBUTION="Economic calendar: https://www.financecalendar.com"

def normalize(payload,now):
    if not isinstance(payload,dict) or not isinstance(payload.get("events"),list):
        raise ValueError("Invalid calendar payload")
    items=payload["events"]\n    if payload.get("error"):raise ValueError("Provider error response")
    total=payload.get("total")
    if not isinstance(total,int) or total>len(items):
        raise ValueError("Incomplete paginated calendar")
    output=[];uncertain=[]
    for r in items:
        if not isinstance(r,dict):raise ValueError("Invalid calendar row")
        if str(r.get("country","")).upper()!="US" or str(r.get("impact","")).lower()!="high":
            continue
        status=str(r.get("status","")).lower()
        if status in ("cancelled","released"):continue
        dt=r.get("time_utc")
        if not dt or status not in ("confirmed","rescheduled"):
            uncertain.append(r.get("name") or r.get("series_code") or "US release")
            continue
        stamp=datetime.fromisoformat(str(dt).replace("Z","+00:00"))
        if stamp.tzinfo is None:raise ValueError("Naive event timestamp")
        stamp=stamp.astimezone(timezone.utc)
        name=str(r.get("name") or r.get("title") or r.get("series_code") or "").strip()
        if not name:raise ValueError("Unnamed US event")
        if now-timedelta(hours=1)<=stamp<=now+timedelta(days=2):
            output.append(Event(stamp,name,"HIGH","USD"))
    return {"events":sorted(output,key=lambda x:x.time_utc),"uncertain":uncertain}

def retrieve(now=None,opener=None):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError("Aware now required")
    params={"country":"US","impact":"high","from":(now-timedelta(days=1)).date().isoformat(),
            "to":(now+timedelta(days=2)).date().isoformat(),"limit":500}
    url=BASE+"?"+urllib.parse.urlencode(params)
    try:
        req=urllib.request.Request(url,headers={"Accept":"application/json","User-Agent":"ReneGoldResearchV4/1.0"})
        with (opener or urllib.request.urlopen)(req,timeout=12) as response:
            data=response.read(2_000_001)
        if len(data)>2_000_000:raise ValueError("Oversized response")
        payload=json.loads(data)
        info=normalize(payload,now)
        # Coverage is explicitly incomplete, so require independent confirmation
        # before treating news gate as verified and allowing trade eligibility.
        return {"verified":False,"status":"UNVERIFIED_FREE_CALENDAR_COVERAGE",
                "events":info["events"],"uncertain":info["uncertain"],
                "fetched_at_utc":now.isoformat(),"attribution":ATTRIBUTION}
    except Exception as exc:
        return {"verified":False,"status":"CALENDAR_UNAVAILABLE_"+type(exc).__name__,
                "events":[],"uncertain":[],"attribution":ATTRIBUTION}

if __name__=="__main__":
    result=retrieve()
    print(json.dumps({"verified":result["verified"],"status":result["status"],
      "events":len(result["events"]),"uncertain":len(result["uncertain"]),
      "attribution":result["attribution"]}))
