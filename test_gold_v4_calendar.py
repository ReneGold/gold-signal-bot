import unittest,json
from datetime import datetime,timezone,timedelta
from gold_v4_calendar import normalize,retrieve
T=datetime(2026,10,26,12,0,tzinfo=timezone.utc)
class Resp:
    def __init__(self,p):self.p=p
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n):return self.p
def provider(req,timeout):return Resp(json.dumps([{"Country":"United States","Importance":3,
    "Event":"CPI","Date":"2026-10-26T12:20:00"}]).encode())
class CalendarTests(unittest.TestCase):
    def test_missing_secret_fails_closed(self):self.assertFalse(retrieve(now=T,key="")["verified"])
    def test_provider_parses_event(self):
        r=retrieve(now=T,key="dummy",opener=provider)
        self.assertEqual(len(r["events"]),1);self.assertFalse(r["verified"])
    def test_only_impact3_us(self):
        rows=[{"Country":"Germany","Importance":3,"Event":"Other","Date":"2026-10-26T12:20:00"},
              {"Country":"United States","Importance":2,"Event":"PMI","Date":"2026-10-26T12:20:00"}]
        self.assertEqual(normalize(rows,T),[])
    def test_bad_date_rejected(self):
        with self.assertRaises(ValueError):normalize([{"Country":"United States","Importance":3,"Event":"CPI","Date":"wrong"}],T)
    def test_fetch_failure_fails_closed(self):
        def bad(req,timeout):raise OSError("failure")
        self.assertFalse(retrieve(now=T,key="dummy",opener=bad)["verified"])
if __name__=="__main__":unittest.main()
