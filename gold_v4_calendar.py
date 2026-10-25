"""Optional Trading Economics USD economic calendar feed for Gold V4 research.
Secret TE_API_KEY must be configured in GitHub. Fail closed on missing/stale data.
Source Date fields are interpreted as UTC ONLY under provider's UTC API convention;
verify this against provider account before production usage.
No orders, no Telegram, no hardcoded secrets.
"""
import json,os,urllib.request,urllib.parse
from datetime import datetime,timedelta,timezone
from gold_news_volatility_filter import Event

def normalize(rows,now):
    if not isinstance(rows,list):raise ValueError("Calendar response must be an array")
    events=[]
    for row in rows:
        if not isinstance(row,dict):raise ValueError("Invalid event row")
        if str(row.get("Country","")).casefold() not in ("united states","usa"):continue
        if str(row.get("Importance",""))!="3":continue
        raw=str(row.get("Date",""))
        try:
            date=datetime.fromisoformat(raw.replace("Z","+00:00"))
            # TE API calendar Date is delivered without offset; source convention
            # needs external confirmation before setting calendar_verified=true.
            if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
            else:date=date.astimezone(timezone.utc)
        except ValueError as exc:raise ValueError("Unparseable calendar event date") from exc
        name=str(row.get("Event") or row.get("Category") or "").strip()
        if not name:raise ValueError("Unnamed high-impact event")
        if now-timedelta(minutes=45)<=date<=now+timedelta(days=2):
            events.append(Event(date,name,"HIGH","USD"))
    return sorted(events,key=lambda x:x.time_utc)

def retrieve(now=None,key=None,opener=None):
    now=now or datetime.now(timezone.utc)
    key=key if key is not None else os.getenv("TE_API_KEY","")
    if not key:return {"verified":False,"reason":"TE_API_KEY_MISSING","events":[]}
    start=(now-timedelta(days=1)).date().isoformat()
    end=(now+timedelta(days=3)).date().isoformat()
    url=("https://api.tradingeconomics.com/calendar/country/united%20states/"
         +start+"/"+end+"?"+urllib.parse.urlencode({"c":key,"f":"json"}))
    try:
        req=urllib.request.Request(url,headers={"Accept":"application/json"})
        with (opener or urllib.request.urlopen)(req,timeout=12) as response:
            raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError("Oversized calendar response")
        rows=json.loads(raw)
        events=normalize(rows,now)
        if not rows:raise ValueError("Empty provider response")
        # Do not treat a parsed response with missing timezone metadata as safely
        # verified until timezone conventions and provider account are confirmed.
        return {"verified":False,"reason":"PROVIDER_TIMEZONE_NOT_INDEPENDENTLY_VERIFIED",
                "events":events,"fetched_utc":now.isoformat()}
    except Exception as exc:
        return {"verified":False,"reason":"CALENDAR_FETCH_OR_PARSE_FAILED:"+type(exc).__name__,
                "events":[]}

if __name__=="__main__":
    result=retrieve()
    print(json.dumps({"calendar_verified":result["verified"],"reason":result["reason"],
           "events":len(result["events"])},ensure_ascii=False))
