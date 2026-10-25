import unittest
from gold_v4_exit_allocation_compare import simulate_alloc
class AllocationTests(unittest.TestCase):
    def trade(self):return {"side":"LONG","entry":"100","sl":"90","opened":"2026-10-26T10:00:00+00:00"}
    def candle(self,low,high):return [{"datetime_utc":"2026-10-26T10:00:00+00:00","open":"100","low":str(low),"high":str(high),"close":"100"}]
    def test_all_targets_20_30_50(self):
        r,_,_ = simulate_alloc(self.trade(),self.candle(95,125),{"2026-10-26T10:00:00+00:00":0},"20_30_50")
        self.assertAlmostEqual(r,1.675)
    def test_all_targets_20_0_80(self):
        r,_,_ = simulate_alloc(self.trade(),self.candle(95,125),{"2026-10-26T10:00:00+00:00":0},"20_0_80")
        self.assertAlmostEqual(r,1.9)
    def test_stop_first(self):
        r,_,events=simulate_alloc(self.trade(),self.candle(85,125),{"2026-10-26T10:00:00+00:00":0},"20_0_80")
        self.assertAlmostEqual(r,-1.05);self.assertEqual(events,"STOP")
if __name__=="__main__":unittest.main()
