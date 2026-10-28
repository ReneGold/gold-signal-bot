#!/usr/bin/env python3
"""Gold historical-data audit only. No trading, no Telegram, no secret logging.

Requests monthly UTC windows from Twelve Data; validates bar ordering/OHLC and reports
missing intervals. Closed-market gaps are marked as candidates, NOT automatically bad data.
Artifacts only: no commit to default branch and no trading-strategy changes.
"""
import csv,json,os,time
from collections import Counter
from datetime import datetime,timedelta,timezone
from pathlib import Path
import requests
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"gold_data_audit"
OUT.mkdir(exist_ok=True)
KEY=os.environ.get("TWELVE_DATA_API_KEY","")
if not KEY:raise RuntimeError("Missing TWELVE_DATA_API_KEY")
SYMBOL="XAU/USD"
START=datetime(2026,8,1,tzinfo=timezone.utc)
END=min(datetime(2026,10,29,tzinfo=timezone.utc),datetime.now(timezone.utc).replace(second=0,microsecond=0))
def months(start,end):
    cur=start
    while cur<end:
        y,m=cur.year,cur.month
        nxt=datetime(y+1,1,1,tzinfo=timezone.utc) if m==12 else datetime(y,m+1,1,tzinfo=timezone.utc)
        yield cur,min(end,nxt)
        cur=nxt
def fetch(interval,lo,hi):
    # Provider end_date is inclusive: overlap boundary by one interval and deduplicate later.
    args=dict(symbol=SYMBOL,interval=interval,timezone="UTC",format="JSON",outputsize=5000,
        start_date=lo.strftime("%Y-%m-%d %H:%M:%S"),
        end_date=hi.strftime("%Y-%m-%d %H:%M:%S"),apikey=KEY)
    for attempt in range(3):
        response=requests.get("https://api.twelvedata.com/time_series",params=args,timeout=40)
        try: data=response.json()
        except ValueError:raise RuntimeError("Invalid response from provider")
        if response.status_code in (429,503) or data.get("code") in (429,):
            if attempt<2:
                time.sleep((attempt+1)*12)
                continue
        response.raise_for_status()
        if data.get("status")=="error":
            # Never leak URL or credentials
            raise RuntimeError(f"Provider rejected {interval} {lo.date()}..{hi.date()}: code={data.get('code')}, message={str(data.get('message',''))[:180]}")
        vals=data.get("values")
        if not isinstance(vals,list):raise RuntimeError("No time series returned")
        if len(vals)>=5000:raise RuntimeError("Provider cap reached; split window")
        return vals
    raise RuntimeError("Provider throttled request after retries")
def check(interval,minute):
    collected=[];counts=[];invalid=[];out_of_range=0
    for lo,hi in months(START,END):
        values=fetch(interval,lo,hi)
        counts.append(dict(start=lo.date().isoformat(),end=hi.date().isoformat(),rows=len(values)))
        for v in values:
            try:
                t=datetime.fromisoformat(v["datetime"])
                t=t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc)
                o,h,l,c=(float(v[k]) for k in ("open","high","low","close"))
                if not (l<=min(o,c)<=max(o,c)<=h and l>0):raise ValueError("OHLC inconsistent")
                if not (START<=t<END):
                    out_of_range+=1;continue
                collected.append((t,o,h,l,c))
            except (KeyError,ValueError,TypeError) as exc:invalid.append(str(exc)[:100])
        # Credit management: Twelve Data plans differ; avoid bursting
        time.sleep(2)
    freq=Counter(r[0] for r in collected)
    unique={r[0]:r for r in collected}
    ordered=[unique[t] for t in sorted(unique)]
    gap_candidates=[]
    for a,b in zip(ordered,ordered[1:]):
        delta_minutes=int((b[0]-a[0]).total_seconds()/60)
        if delta_minutes>minute:
            gap_candidates.append(dict(after=a[0].isoformat(),before=b[0].isoformat(),
                missing_slots=delta_minutes//minute-1,elapsed_minutes=delta_minutes,
                note="May be expected market close/weekend or missing vendor data"))
    outfile=OUT/f"gold_{interval}_2026_aug_oct.csv"
    with outfile.open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f);w.writerow(["utc","open","high","low","close"])
        for t,o,h,l,c in ordered:w.writerow([t.isoformat(),o,h,l,c])
    report=dict(interval=interval,bar_minutes=minute,rows=len(ordered),
        first_utc=ordered[0][0].isoformat() if ordered else None,
        last_utc=ordered[-1][0].isoformat() if ordered else None,
        duplicate_timestamps=sum(x-1 for x in freq.values()),
        invalid_rows=len(invalid),invalid_examples=invalid[:5],out_of_range_rows=out_of_range,
        gap_candidate_count=len(gap_candidates),
        gap_candidates=gap_candidates[:100],monthly_requests=counts,
        note="All gaps need manual market-session review; do not interpolate price candles")
    print(f"{interval}: rows={report['rows']}, duplicates={report['duplicate_timestamps']}, invalid={report['invalid_rows']}, gap candidates={report['gap_candidate_count']}")
    if not ordered:raise RuntimeError("No historical rows retrieved")
    return report
report=dict(symbol=SYMBOL,requested_start_utc=START.isoformat(),requested_end_exclusive_utc=END.isoformat(),
    source="Twelve Data historical OHLC, UTC",limitations="Provider availability/plan and market-closed periods may limit coverage. No order fills or performance calculated.",
    intervals=[check("15min",15),check("1h",60)])
(OUT/"gold_data_quality_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("Audit report created. No trading decisions or Telegram messages sent.")
