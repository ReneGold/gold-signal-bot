import unittest
from datetime import datetime,timedelta,timezone
from gold_v5_regime_backtest import Bar,atr,ema,gold_session,simulate,summarize

class RegimeBacktestTests(unittest.TestCase):
    def test_ema(self):
        self.assertEqual(ema([10,10,10],20),[10,10,10])
    def test_atr_constant(self):
        x=[Bar(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=15*i),100,101,99,100) for i in range(20)]
        self.assertAlmostEqual(atr(x)[19],2)
    def test_closed_chicago_session(self):
        self.assertFalse(gold_session(datetime(2026,11,7,12,tzinfo=timezone.utc)))
    def test_empty_summary(self):
        self.assertIsNone(summarize([])["win_rate"])
    def test_no_past_bar_trades_without_data(self):
        x=[Bar(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(minutes=15*i),100,101,99,100) for i in range(40)]
        self.assertEqual(simulate(x,[], "bitcoin","frozen"),[])
    def test_no_lookahead_on_duplicate_bar(self):
        self.assertEqual(summarize([{"R":2},{"R":-1}])["net_R"],1)
if __name__=="__main__":unittest.main()
