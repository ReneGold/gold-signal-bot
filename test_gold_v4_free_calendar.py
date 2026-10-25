import unittest,json
from datetime import datetime,timezone
from gold_v4_free_calendar import retrieve,normalize
T=datetime(2026,10,26,12,0,tzinfo=timezone.utc)
class Resp:
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n):return self.data
def response(payload):
    def open_fn(req,timeout):
        r=Resp();r.data=json.dumps(payload).encode();return r
    return open_fn
class FreeCalendarTests(unittest.TestCase):
    def test_confirmed_event(self):
        p={"events":[{"name":"US CPI","country":"US","impact":"high","status":"confirmed",
             "time_utc":"2026-10-26T12:30:00+00:00"}],"total":1}
        r=retrieve(T,response(p))
        self.assertEqual(len(r["events"]),1)
        self.assertFalse(r["verified"])
    def test_unknown_time_not_approved(self):
        p={"events":[{"name":"US CPI","country":"US","impact":"high","status":"estimated","time_utc":None}],"total":1}
        r=retrieve(T,response(p))
        self.assertTrue(r["uncertain"])
        self.assertFalse(r["verified"])
    def test_pagination_rejected(self):
        with self.assertRaises(ValueError):normalize({"events":[],"total":5},T)
    def test_failure_fails_closed(self):
        def fail(req,timeout):raise OSError("network")
        self.assertFalse(retrieve(T,fail)["verified"])
    def test_cancelled_ignored(self):
        x=normalize({"events":[{"name":"CPI","country":"US","impact":"high","status":"cancelled","time_utc":None}],"total":1},T)
        self.assertFalse(x["events"])
if __name__=="__main__":unittest.main()
