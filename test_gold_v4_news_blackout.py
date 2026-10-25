"""Deterministic US high-impact news blackout checks for V4 research only.
Synthetic CPI/NFP/FOMC event labels and illustrative UTC timestamps, NOT an
assertion of actual publication schedule. No orders or live authorization.
"""
import unittest
from datetime import datetime,timedelta,timezone
from gold_news_volatility_filter import Event,check,GatePolicy

ANCHOR=datetime(2026,10,29,13,30,tzinfo=timezone.utc)
def decision(minute_offset,event_label="US CPI",impact="HIGH",currency="USD"):
    ev=Event(ANCHOR,event_label,impact,currency)
    current=ANCHOR+timedelta(minutes=minute_offset)
    return check(assessed_at_utc=current,events=[ev],latest_close=4000,
                 latest_true_range=9,atr_15m=8)

class NewsBlackoutIntegrationTests(unittest.TestCase):
    def test_block_30_before(self):
        for label in ("US CPI","US NFP","FOMC Rate Decision"):
            with self.subTest(label=label):
                out=decision(-30,label)
                self.assertFalse(out["approved"])
                self.assertIn("HIGH_IMPACT_USD_NEWS_WINDOW",out["reasons"])
    def test_block_just_before(self):
        self.assertFalse(decision(-1)["approved"])
    def test_block_at_release(self):
        self.assertFalse(decision(0)["approved"])
    def test_block_just_after(self):
        self.assertFalse(decision(1)["approved"])
    def test_block_30_after(self):
        self.assertFalse(decision(30)["approved"])
    def test_outside_before(self):
        out=decision(-31)
        self.assertTrue(out["approved"])
        self.assertNotIn("HIGH_IMPACT_USD_NEWS_WINDOW",out["reasons"])
    def test_outside_after(self):
        self.assertTrue(decision(31)["approved"])
    def test_low_impact_does_not_create_news_blackout(self):
        self.assertTrue(decision(0,impact="LOW")["approved"])
    def test_non_usd_not_blocked_by_us_only_policy(self):
        self.assertTrue(decision(0,currency="EUR")["approved"])
    def test_independent_volatility_block(self):
        ev=Event(ANCHOR,"US CPI")
        result=check(assessed_at_utc=ANCHOR-timedelta(minutes=31),events=[ev],
                     latest_close=4000,latest_true_range=30,atr_15m=8)
        self.assertFalse(result["approved"])
        self.assertIn("EXCESSIVE_15M_RANGE",result["reasons"])
    def test_no_events_is_unknown_not_verified(self):
        result=check(assessed_at_utc=ANCHOR,events=[],latest_close=4000,
                     latest_true_range=9,atr_15m=8)
        self.assertEqual(result["calendar_status"],"UNKNOWN_NO_EVENTS_SUPPLIED")
        # The news gate by itself evaluates known events only. V4 pipeline must
        # still reject incomplete calendar via its independent verification gate.
if __name__=="__main__":unittest.main()
