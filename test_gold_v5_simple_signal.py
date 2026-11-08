"""Offline tests only: no API, broker, GitHub actions, or Telegram."""
import unittest
from datetime import datetime, timedelta, timezone
from gold_v5_simple_signal import Bar, decide, risk_budget, validate

UTC=timezone.utc
def series(n, minutes, start, initial=100, step=0.2):
    return [Bar(start + timedelta(minutes=minutes*i),
                initial+step*i,initial+step*i+1,initial+step*i-1,initial+step*i+0.1)
            for i in range(n)]

class GoldSimpleTests(unittest.TestCase):
    def setUp(self):
        self.h1=series(80,60,datetime(2026,11,1,tzinfo=UTC),initial=100,step=0.4)
        self.m15=series(80,15,self.h1[-1].start-timedelta(hours=19),
                        initial=110,step=0.2)
        # Last H1 bar closes at 08:00; last 15m bar closes there too.
        self.assertEqual(self.h1[-1].start+timedelta(hours=1),
                         self.m15[-1].start+timedelta(minutes=15))
        self.now=self.m15[-1].start+timedelta(minutes=15)
    def test_no_future_h1(self):
        future=self.h1+[Bar(self.h1[-1].start+timedelta(hours=1),160,161,159,160)]
        self.assertEqual(decide(self.m15,future,self.now)["reason"],"H1_NOT_CLOSED_OR_STALE")
    def test_stale_signal(self):
        self.assertEqual(decide(self.m15,self.h1,self.now+timedelta(minutes=16))["reason"],"STALE_OR_OPEN_BAR")
    def test_recent_gap_rejected(self):
        bars=list(self.m15)
        last=bars[-1]
        bars[-1]=Bar(last.start+timedelta(minutes=15),last.open,last.high,last.low,last.close)
        with self.assertRaisesRegex(ValueError,"Gap in latest"):decide(bars,self.h1,self.now)
    def test_historical_weekend_gap_allowed(self):
        bars=list(self.m15)
        shift=timedelta(hours=2)
        bars[0]=Bar(bars[0].start-shift,bars[0].open,bars[0].high,bars[0].low,bars[0].close)
        validate(bars,15)
    def test_no_matching_signal_on_plain_trend(self):
        r=decide(self.m15,self.h1,self.now)
        self.assertEqual(r["status"],"NO_SIGNAL")
    def test_budget(self):
        self.assertEqual(risk_budget(5000,0,0,0),25)
        self.assertEqual(risk_budget(5000,40,0,0),10)
        self.assertEqual(risk_budget(5000,50,0,0),0)
        self.assertEqual(risk_budget(5000,0,2,0),0)
        self.assertEqual(risk_budget(5000,0,0,1),0)
        with self.assertRaises(ValueError):risk_budget(5000,-1,0,0)
    def test_no_market_order_code(self):
        self.assertFalse(hasattr(__import__("gold_v5_simple_signal"),"place_order"))

if __name__=="__main__":unittest.main()
