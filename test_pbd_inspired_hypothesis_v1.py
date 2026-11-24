import unittest
from datetime import datetime,timedelta,timezone
from pbd_inspired_hypothesis_v1 import setup,backtest,split,stats
T=datetime(2026,11,17,0,tzinfo=timezone.utc)
def bar(i,o,c,h=None,l=None):
    return (T+timedelta(minutes=15*i),float(o),float(max(o,c)+.2 if h is None else h),
            float(min(o,c)-.2 if l is None else l),float(c))
def synthetic():
    a=[bar(i,100,100,h=101,l=99) for i in range(20)]
    a += [bar(20+i,100+i,101+i) for i in range(4)]
    a += [bar(24+i,104.1,104.2,h=104.4,l=104) for i in range(4)]
    a += [bar(28,104.1,103.9,h=104.2,l=103.7)]
    return a
class PbdHypothesisTests(unittest.TestCase):
    def test_detects_p_failure_from_closed_candles(self):
        s=setup(synthetic())
        self.assertIsNotNone(s)
        self.assertAlmostEqual(s["upper"],104.2)
        self.assertAlmostEqual(s["lower"],104.1)
    def test_no_future_bar_in_signal(self):
        a=synthetic()
        self.assertEqual(setup(a),setup(a+[bar(29,103.5,101)]))
    def test_no_signal_without_impulse(self):
        a=synthetic()
        for i in range(20,24):a[i]=bar(i,100,100.1)
        self.assertIsNone(setup(a))
    def test_reject_gap(self):
        a=synthetic()
        a[25]=(a[25][0]+timedelta(minutes=15),*a[25][1:])
        self.assertIsNone(setup(a))
    def test_first_bar_stop_before_target(self):
        a=synthetic()+[bar(29,103.9,102.0,h=105.0,l=101.0)]
        a += [bar(i,100,100) for i in range(30,50)]
        trades,_,_=backtest(a,cost=0.8)
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]["exit_reason"],"STOP")
        self.assertLess(trades[0]["net_R"],-1)
    def test_missing_exit_bar_unresolved(self):
        a=synthetic()+[bar(i,103.9,103.7,h=104,l=103.5) for i in range(29,33)]
        a.append(bar(34,103.9,103.7,h=104,l=103.5))
        a += [bar(i,100,100) for i in range(35,56)]
        trades,_,unresolved=backtest(a)
        self.assertEqual(len(trades),0)
        self.assertEqual(len(unresolved),1)
    def test_no_trade_statistics(self):
        self.assertEqual(stats([])["trades"],0)
        self.assertIsNone(stats([])["average_R"])
if __name__=="__main__":unittest.main()
