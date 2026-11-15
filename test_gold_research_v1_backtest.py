"""Research backtest safety tests; no broker, API or data downloads."""
import unittest
from datetime import datetime,timedelta,timezone
from gold_research_v1 import Bar
from gold_research_v1_backtest import quality,replay
UTC=timezone.utc

def make_bars(n,minutes,start,step):
    return [Bar(start+timedelta(minutes=i*minutes),100+i*step,
                101+i*step,99+i*step,100+i*step) for i in range(n)]

class ResearchBacktestTests(unittest.TestCase):
    def test_quality_full_hourly_aggregation(self):
        start=datetime(2026,8,3,tzinfo=UTC)
        f=make_bars(400,15,start,0)
        h=[Bar(f[i].start,f[i].open,max(x.high for x in f[i:i+4]),
               min(x.low for x in f[i:i+4]),f[i+3].close) for i in range(0,400,4)]
        report=quality(f,h)
        self.assertEqual(report["h1_blocks_price_mismatch"],0)
        self.assertEqual(report["h1_blocks_with_all_four_15m"],100)
    def test_missing_hourly_data_detected(self):
        start=datetime(2026,8,3,tzinfo=UTC)
        f=make_bars(400,15,start,0)
        h=[Bar(f[i].start,100,101,99,100) for i in range(0,400,4)]
        f.pop(6)
        report=quality(f,h)
        self.assertGreater(report["h1_blocks_unmatched_missing_15m"],0)
    def test_negative_cost_rejected(self):
        start=datetime(2026,8,3,tzinfo=UTC)
        f=make_bars(500,15,start,0.01)
        h=make_bars(125,60,start,0.04)
        with self.assertRaises(ValueError):replay(f,h,extra_round_trip=-1)
    def test_one_strategy_no_future_orders(self):
        import gold_research_v1_backtest
        self.assertFalse(hasattr(gold_research_v1_backtest,"place_order"))
if __name__=="__main__":unittest.main()
