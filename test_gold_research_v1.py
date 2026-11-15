"""Tests for new, disconnected Gold research candidate. No paid data or trading."""
import unittest
from datetime import datetime,timedelta,timezone
from gold_research_v1 import Bar,candidate,allowed_risk_eur

UTC=timezone.utc
def bars(n,interval,end,base=100,increment=0.1):
    start=end-timedelta(minutes=n*interval)
    return [Bar(start+timedelta(minutes=i*interval),base+i*increment,
                base+i*increment+1,base+i*increment-1,base+i*increment+0.1)
            for i in range(n)]

class TestGoldResearchV1(unittest.TestCase):
    def setUp(self):
        self.end=datetime(2026,11,10,12,0,tzinfo=UTC)
        self.h1=bars(80,60,self.end,100,0.4)
        self.m15=bars(80,15,self.end,100,0.2)
    def test_risk_budget(self):
        self.assertEqual(allowed_risk_eur(5000,0,0,0),25)
        self.assertEqual(allowed_risk_eur(5000,40,0,0),10)
        self.assertEqual(allowed_risk_eur(5000,50,0,0),0)
        self.assertEqual(allowed_risk_eur(5000,0,2,0),0)
        self.assertEqual(allowed_risk_eur(5000,0,0,1),0)
    def test_no_future_h1(self):
        future=self.h1+[Bar(self.end,150,152,149,151)]
        self.assertEqual(candidate(self.m15,future,self.end)["reason"],"h1_stale_or_incomplete")
    def test_no_open_candle(self):
        self.assertEqual(candidate(self.m15,self.h1,self.end-timedelta(minutes=1))["reason"],"not_current_closed_15m")
    def test_stale_candle(self):
        self.assertEqual(candidate(self.m15,self.h1,self.end+timedelta(minutes=16))["reason"],"not_current_closed_15m")
    def test_latest_gap_rejected(self):
        b=list(self.m15)
        last=b[-1]
        b[-1]=Bar(last.start+timedelta(minutes=15),last.open,last.high,last.low,last.close)
        with self.assertRaisesRegex(ValueError,"consecutive"):candidate(b,self.h1,self.end)
    def test_no_broker_or_order_code(self):
        import gold_research_v1
        self.assertFalse(hasattr(gold_research_v1,"place_order"))
    def test_valid_candidate_requires_breakout(self):
        # strong 1h-up context, closed 15m breakout of previous 20 highs
        b=list(self.m15)
        last=b[-1]
        b[-1]=Bar(last.start,last.open,150,last.low,149)
        r=candidate(b,self.h1,self.end)
        self.assertEqual(r["status"],"PAPER_CANDIDATE")
        self.assertEqual(r["side"],"LONG")
        self.assertGreater(r["indicative_stop_distance"],0)
    def test_no_breakout_no_candidate(self):
        r=candidate(self.m15,self.h1,self.end)
        self.assertEqual(r["status"],"NO_SIGNAL")
if __name__=="__main__":unittest.main()
