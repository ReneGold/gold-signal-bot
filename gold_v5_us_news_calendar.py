#!/usr/bin/env python3
"""Read-only US high-impact macro calendar via public XOOMAR JSON endpoint.
Calendar does NOT alter paper signals and is NOT a verified execution gate.
Fail unknown on network/schema/staleness/coverage errors. No false 'all clear'.
"""
import json, urllib.request, math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
URL="https://xoomar.com/api/markets/calendar?importance=high"
NOW=datetime.now(timezone.utc)
TARGETS={
    "NFP":("nonfarm payroll","employment situation"),
    "CPI":("consumer price index","cpi"),
    "PPI":("producer price index","ppi"),
    "PCE":("personal income and outlays","pce"),
    "FOMC":("fomc","federal funds","fed rate decision","interest rate decision"),
}
result={"generated_utc":NOW.isoformat(),"mode":"OBSERVATION_ONLY",
    "provider":"XOOMAR (third-party aggregation of agency schedules)",
    "source_url":URL,"source_status":"UNAVAILABLE",
    "selected_categories":list(TARGETS),"future_events":[],
    "near_release_window":None,"time_window_minutes":{"before":30,"after":30},
    "trading_filter_active":False,"errors":[],
    "coverage_scope":"Selected US high-impact releases only; surprises or schedule changes possible.",
    "caution":"Third-party unverified calendar. Empty list or outage NEVER means no news risk."}
try:
    req=urllib.request.Request(URL,headers={
        "User-Agent":"GoldV5-Research-Calendar/1.0",
        "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as f:
        data=f.read(750001)
    if len(data)>750000:raise ValueError("Response too large")
    payload=json.loads(data.decode("utf-8"))
    rows=payload.get("data") if isinstance(payload,dict) else None
    if not isinstance(rows,list) or not rows:raise ValueError("Missing/nonempty calendar data list")
    seen=set()
    for event in rows:
        if not isinstance(event,dict):continue
        name=event.get("eventName")
        stamp=event.get("scheduledAt")
        if not isinstance(name,str) or not isinstance(stamp,str):continue
        lo=name.lower()
        cat=next((key for key,terms in TARGETS.items() if any(t in lo for t in terms)),None)
        if not cat:continue
        try:
            dt=datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if dt.tzinfo is None:raise ValueError("Time missing UTC offset")
            dt=dt.astimezone(timezone.utc)
        except ValueError:
            result["errors"].append("Invalid timestamp for "+cat)
            continue
        if NOW-timedelta(minutes=30)<=dt<=NOW+timedelta(days=32):
            key=(cat,dt.isoformat())
            if key in seen:continue
            seen.add(key)
            result["future_events"].append({"category":cat,"title":name,
                 "release_utc":dt.isoformat(),
                 "release_berlin":dt.astimezone(ZoneInfo("Europe/Berlin")).isoformat(),
                 "minutes_until":round((dt-NOW).total_seconds()/60,1),
                 "source":"XOOMAR; confirm with original agency"})
    result["future_events"].sort(key=lambda e:e["release_utc"])
    # A valid response without relevant events is not an all-clear.
    if not result["future_events"]:
        result["source_status"]="UNCERTAIN_NO_MATCHING_EVENTS"
        result["errors"].append("No matching events; cannot verify news-free window")
    elif result["errors"]:
        result["source_status"]="PARTIAL_UNVERIFIED"
    else:
        result["source_status"]="THIRD_PARTY_UNVERIFIED"
    result["near_release_window"]=any(-30<=e["minutes_until"]<=30 for e in result["future_events"])
except Exception as exc:
    result["errors"].append(type(exc).__name__+": "+str(exc)[:170])
(ROOT/"gold_v5_us_news_calendar.json").write_text(
    json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
