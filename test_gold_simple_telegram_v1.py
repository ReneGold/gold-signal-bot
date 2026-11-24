import unittest
from datetime import datetime,timedelta,timezone
from gold_simple_telegram_v1 import evaluate,closed_bars
T=datetime(2026,11,24,tzinfo=timezone.utc)
def make(closes):
    return [{"time":T+timedelta(minutes=15*i),"open":v,"high":v+1,"low":v-1,"close":v} for i,v in enumerate(closes)]
class GoldSimpleTests(unittest.TestCase):
    def test_no_candles(self):self.assertIsNone(evaluate([]))
    def test_no_cross(self):self.assertIsNone(evaluate(make([100.0]*80)))
    def test_missing_candles(self):
        bars=make([100.0]*90)
        bars[-2]["time"]+=timedelta(minutes=5)
        self.assertIsNone(evaluate(bars))
    def test_signal_on_closed_bar(self):
        # No assertion of result direction, but deterministic and no modifications to input
        bars=make([100]*40+[99]*15+[100+i*1.8 for i in range(25)])
        original=bars[-1].copy()
        result=evaluate(bars)
        self.assertEqual(original,bars[-1])
        if result:
            self.assertGreater(result["target"],result["entry"]) if "LONG" in result["side"] else self.assertLess(result["target"],result["entry"])
    def test_filter_unfinished(self):
        now=T+timedelta(minutes=30)
        payload={"values":[{"datetime":"2026-11-24 00:00:00","open":"100","high":"101","low":"99","close":"100"},{"datetime":"2026-11-24 00:15:00","open":"100","high":"101","low":"99","close":"100"}]}
        self.assertEqual(len(closed_bars(payload,now)),1)
if __name__=="__main__":unittest.main()
