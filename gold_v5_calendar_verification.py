#!/usr/bin/env python3
"""Compare third-party observed US releases to a time-limited, manually verified agency reference.
Read-only, fail-unknown. Never treats unlisted events or stale references as safe.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
P=Path(__file__).resolve().parent
calendar=json.loads((P/"gold_v5_us_news_calendar.json").read_text(encoding="utf-8"))
reference=json.loads((P/"gold_v5_official_calendar_reference.json").read_text(encoding="utf-8"))
now=datetime.now(timezone.utc)
expiry=datetime.fromisoformat(reference["valid_through_utc"])
known={(r["category"],datetime.fromisoformat(r["release_utc"])):r for r in reference["events"]}
events=[]
for event in calendar.get("future_events",[]):
    try: key=(event["category"],datetime.fromisoformat(event["release_utc"]))
    except (KeyError,ValueError,TypeError):
        events.append({"event":event,"status":"UNVERIFIED_INVALID_TIME"})
        continue
    record=known.get(key)
    events.append({"category":key[0],"release_utc":key[1].isoformat(),
       "verification":"MATCHES_SNAPSHOT" if record and now<=expiry else "UNVERIFIED",
       "source_url":record["source_url"] if record and now<=expiry else None})
report={"checked_utc":now.isoformat(),"mode":"OBSERVATION_ONLY",
   "third_party_status":calendar.get("source_status","UNAVAILABLE"),
   "reference_valid":now<=expiry,
   "source_reference_date":reference["verification_date_utc"],
   "events":events,
   "confirmed_matches":sum(e.get("verification")=="MATCHES_SNAPSHOT" for e in events),
   "matched_event_count":len(events),
   "fully_verified_live_calendar":False,
   "missing_categories":[r["category"] for r in reference["events"] if datetime.fromisoformat(r["release_utc"])>=now and not any(e.get("category")==r["category"] and e.get("verification")=="MATCHES_SNAPSHOT" for e in events)],
   "trading_filter_active":False,
   "warning":"Manual snapshot comparison is not live official verification; missing and rescheduled data may remain unrecognized. Do not change trades."}
(P/"gold_v5_calendar_verification.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2,ensure_ascii=False))
