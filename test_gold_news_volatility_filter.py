import unittest
from datetime import datetime,timedelta,timezone
from gold_news_volatility_filter import Event,check
T=datetime(2026,10,26,12,30,tzinfo=timezone.utc)
class GateTests(unittest.TestCase):
    def run_gate(self,**kw):
        p=dict(assessed_at_utc=T,events=[],latest_close=4000,latest_true_range=10,atr_15m=8)
        p.update(kw);return check(**p)
    def test_normal(self):self.assertTrue(self.run_gate()["approved"])
    def test_calendar_unknown(self):self.assertEqual(self.run_gate()["calendar_status"],"UNKNOWN_NO_EVENTS_SUPPLIED")
    def test_upcoming_high_usd(self):
        x=self.run_gate(events=[Event(T+timedelta(minutes=25),"US CPI")])
        self.assertFalse(x["approved"])
    def test_recent_high_usd(self):
        self.assertFalse(self.run_gate(events=[Event(T-timedelta(minutes=25),"FOMC")])["approved"])
    def test_outside_window(self):
        self.assertTrue(self.run_gate(events=[Event(T+timedelta(minutes=31),"NFP")])["approved"])
    def test_low_impact(self):
        self.assertTrue(self.run_gate(events=[Event(T,"minor","LOW")])["approved"])
    def test_non_usd(self):
        self.assertTrue(self.run_gate(events=[Event(T,"Euro data","HIGH","EUR")])["approved"])
    def test_excessive_range(self):
        self.assertFalse(self.run_gate(latest_true_range=25)["approved"])
    def test_atr_too_low(self):
        self.assertFalse(self.run_gate(atr_15m=.5)["approved"])
    def test_atr_too_high(self):
        self.assertFalse(self.run_gate(atr_15m=20)["approved"])
    def test_timezone_validation(self):
        with self.assertRaises(ValueError):self.run_gate(events=[Event(T.replace(tzinfo=None),"bad")])
if __name__=="__main__":unittest.main()
