import unittest
from gold_v4_paired_exit_backtest import simulate,metrics

class PairedExitTests(unittest.TestCase):
    def test_simple_full_target(self):
        t={"side":"LONG","entry":"100","sl":"90","opened":"2026-10-26T10:00:00+00:00","closed":"2026-10-26T10:30:00+00:00"}
        bars=[{"datetime_utc":"2026-10-26T10:00:00+00:00","open":"100","high":"123","low":"95","close":"120"}]
        r,stamp,events=simulate(t,bars,{bars[0]["datetime_utc"]:0})
        self.assertAlmostEqual(r,1.525)
        self.assertIn("TP3",events)
    def test_conservative_stop_first(self):
        t={"side":"LONG","entry":"100","sl":"90","opened":"2026-10-26T10:00:00+00:00","closed":"2026-10-26T10:30:00+00:00"}
        bars=[{"datetime_utc":"2026-10-26T10:00:00+00:00","open":"100","high":"130","low":"88","close":"100"}]
        r,_,events=simulate(t,bars,{bars[0]["datetime_utc"]:0})
        self.assertAlmostEqual(r,-1.05)
        self.assertEqual(events,"STOP")
    def test_metrics(self):
        result=metrics([1,-1,1])
        self.assertEqual(result["trades"],3)
        self.assertAlmostEqual(result["sum_R"],1)
if __name__=="__main__":unittest.main()
