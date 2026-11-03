import tempfile
import unittest
from pathlib import Path
from gold_v5_decision_explain import decide, make_report, save_observation

BASE=dict(fresh=True,market_open=True,sideways=True,trend=True,touched=True,
          confirmed=True,active=False,risk_allowed=True,already_seen=False)

class DecisionExplainTests(unittest.TestCase):
    def test_eligible_has_no_fake_score(self):
        d=decide(**BASE)
        self.assertTrue(d["qualified"])
        self.assertIsNone(d["score"])
    def test_blocking_order(self):
        d=decide(**{**BASE,"sideways":False,"confirmed":False})
        self.assertEqual(d["primary_reason"],"MARKET_PHASE_BLOCKED")
        self.assertIn("NO_BREAKOUT_CONFIRMATION",d["all_reasons"])
    def test_stale_not_claimed(self):
        d=decide(**{**BASE,"fresh":False})
        self.assertFalse(d["qualified"])
        self.assertEqual(d["primary_reason"],"STALE_OR_MISSED_RUN")
    def test_log_deduplicates_candle(self):
        with tempfile.TemporaryDirectory() as p:
            path=Path(p)/"log.json"
            item={"candle_utc":"2026-11-03T08:15:00+00:00","fresh":True,"primary_reason":"NO_EMA_TREND"}
            self.assertEqual(len(save_observation(path,item)),1)
            self.assertEqual(len(save_observation(path,item)),1)
            self.assertEqual(make_report(save_observation(path,item))["observed_closed_candles"],1)

if __name__ == "__main__":
    unittest.main()
