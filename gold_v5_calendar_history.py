#!/usr/bin/env python3
"""Append-only observations of third-party US release schedules (no trade changes).
Tracks first/last seen, possible rescheduling and feed outages; never assumes
a missing event was cancelled. This is not an official historical calendar.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=json.loads((ROOT/"gold_v5_us_news_calendar.json").read_text(encoding="utf-8"))
verification=json.loads((ROOT/"gold_v5_calendar_verification.json").read_text(encoding="utf-8"))
archive_path=ROOT/"gold_v5_calendar_history.json"
old=json.loads(archive_path.read_text(encoding="utf-8")) if archive_path.exists() else {"observations":[]}
observations=old.get("observations",[])
if not isinstance(observations,list):raise ValueError("Malformed prior history")
now=datetime.now(timezone.utc).isoformat()
valid_feed=source.get("source_status") in ("THIRD_PARTY_UNVERIFIED","PARTIAL_UNVERIFIED")
verified={(e.get("category"),e.get("release_utc")):e.get("verification") for e in verification.get("events",[])}
new=0
if valid_feed:
    for event in source.get("future_events",[]):
        category=event.get("category")
        when=event.get("release_utc")
        if not category or not when:continue
        key=(category,when)
        previous=next((r for r in observations if (r.get("category"),r.get("release_utc"))==key),None)
        if previous:
            previous["last_seen_utc"]=now
            previous["seen_count"]=previous.get("seen_count",1)+1
            if verified.get(key)=="MATCHES_SNAPSHOT":previous["reference_match_seen"]=True
        else:
            observations.append({"category":category,"release_utc":when,
                "title":event.get("title"),"first_seen_utc":now,"last_seen_utc":now,
                "seen_count":1,"reference_match_seen":verified.get(key)=="MATCHES_SNAPSHOT",
                "source":"XOOMAR third-party calendar"})
            new+=1
# Different dates for same event category can be consecutive releases: DO NOT
# interpret them as revisions without a unique stable upstream release ID.
observations.sort(key=lambda x:(x.get("release_utc",""),x.get("category","")))
archive_path.write_text(json.dumps({"observations":observations},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
report={"checked_utc":now,"source_status":source.get("source_status"),
        "new_unique_category_time_pairs":new,"archived_pairs":len(observations),
        "current_feed_usable":valid_feed,
        "schedule_changes_proven":False,
        "fomc_currently_seen":any(e.get("category")=="FOMC" for e in source.get("future_events",[])),
        "uncertainties":[
            "Calendar events have no stable unique release identifier; apparent date changes cannot be confidently detected.",
            "Missing events or provider outages do not mean cancellation or a news-free trading session.",
            "Only events observed after archive installation are captured, not missing historical news.",
            "FOMC dates, official updates and unexpected news are not guaranteed by this feed.",
            "Trading rules remain unchanged; no active news filter."
        ]}
(ROOT/"gold_v5_calendar_history_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
