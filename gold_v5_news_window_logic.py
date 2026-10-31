"""Pure, research-only blackout matching. One signal is counted once even if events overlap."""
from datetime import datetime

def matching_events(decision_utc, events, minutes):
    decision=datetime.fromisoformat(decision_utc)
    matching=[]
    for event in events:
        stamp=datetime.fromisoformat(event["release_utc"])
        if decision.tzinfo is None or stamp.tzinfo is None:
            raise ValueError("Timestamp must contain timezone")
        if abs((decision-stamp).total_seconds())<=minutes*60:
            matching.append(event)
    return matching
