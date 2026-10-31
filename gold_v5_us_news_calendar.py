#!/usr/bin/env python3
"""Official BLS economic-calendar watcher (diagnostic only, no trading decisions).
Reads the BLS public ICS feed; reports unavailable rather than guessing if fetch fails.
"""
import json, re, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
URL="https://www.bls.gov/schedule/news_release/bls.ics"
NY=ZoneInfo("America/New_York")
now=datetime.now(timezone.utc)
report={"generated_utc":now.isoformat(),"mode":"OBSERVATION_ONLY",
        "provider":"US Bureau of Labor Statistics",
        "source_url":URL,"source_status":"UNAVAILABLE",
        "selected_categories":["Employment Situation (NFP)","Consumer Price Index (CPI)","Producer Price Index (PPI)"],
        "coverage_scope":"BLS releases only. Does not cover FOMC, BEA/PCE, speeches or unexpected news.",
        "future_events":[],"near_release_window":None,
        "time_window_minutes":{"before":30,"after":30},
        "trading_filter_active":False,"errors":[],
        "caution":"Missing or incomplete calendar must never imply no news risk."}

def unfold(data):
    out=[]
    for line in data.replace("\r\n","\n").split("\n"):
        if line.startswith((" ","\t")) and out:
            out[-1]+=line[1:]
        else:out.append(line)
    return out

def parse_start(value,field):
    match=re.match(r"^(\d{8})(?:T(\d{6})(Z)?)?$",value)
    if not match:raise ValueError("Unknown ICS DTSTART")
    ymd,clock,zulu=match.groups()
    if not clock:raise ValueError("All-day calendar item, time not verified")
    dt=datetime.strptime(ymd+clock,"%Y%m%d%H%M%S")
    if zulu:return dt.replace(tzinfo=timezone.utc)
    zone=NY
    m=re.search(r"TZID=([^;:]+)",field)
    if m:
        tz=m.group(1)
        try:zone=ZoneInfo(tz)
        except Exception:raise ValueError("Unrecognized ICS timezone "+tz)
    return dt.replace(tzinfo=zone).astimezone(timezone.utc)

try:
    req=urllib.request.Request(URL,headers={"User-Agent":"GoldV5-ResearchCalendar/1.0 (read-only)"})
    with urllib.request.urlopen(req,timeout=15) as f:
        raw=f.read(1_500_001)
    if len(raw)>1_500_000:raise ValueError("ICS response exceeded size limit")
    text=raw.decode("utf-8-sig")
    if "BEGIN:VCALENDAR" not in text:raise ValueError("No valid VCALENDAR header")
    parts=[]
    item=None
    for line in unfold(text):
        if line=="BEGIN:VEVENT":item={}
        elif line=="END:VEVENT":
            if item is not None:parts.append(item)
            item=None
        elif item is not None and ":" in line:
            key,value=line.split(":",1)
            if key.startswith("SUMMARY"):item["summary"]=value
            elif key.startswith("DTSTART"):item["start_field"]=key;item["start"]=value
    for item in parts:
        title=item.get("summary","")
        low=title.lower()
        if "employment situation" in low:cat="Employment Situation (NFP)"
        elif "consumer price index" in low:cat="Consumer Price Index (CPI)"
        elif "producer price index" in low:cat="Producer Price Index (PPI)"
        else:continue
        try:start=parse_start(item["start"],item["start_field"])
        except (ValueError,KeyError) as exc:
            report["errors"].append("Event time not verified: "+cat+" ("+str(exc)+")")
            continue
        if now-timedelta(minutes=30)<=start<=now+timedelta(days=45):
            report["future_events"].append({"category":cat,"title":title,
                "release_utc":start.isoformat(),
                "release_berlin":start.astimezone(ZoneInfo("Europe/Berlin")).isoformat(),
                "minutes_until":round((start-now).total_seconds()/60,1),
                "source":"BLS"})
    report["future_events"].sort(key=lambda x:x["release_utc"])
    report["source_status"]="PARTIAL" if report["errors"] else "OK_BLS_ONLY"
    report["near_release_window"]=any(-30<=x["minutes_until"]<=30 for x in report["future_events"])
    if not report["future_events"]:report["errors"].append("No matching upcoming BLS items found in selected window; coverage uncertain.")
except Exception as exc:
    report["errors"].append(type(exc).__name__+": "+str(exc)[:180])
(ROOT/"gold_v5_us_news_calendar.json").write_text(
    json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
