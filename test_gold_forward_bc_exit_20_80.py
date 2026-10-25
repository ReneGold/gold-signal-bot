import unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from gold_forward_bc_exit_20_80 import add_signals,update
T=datetime(2026,10,26,10,0,tzinfo=timezone.utc)
def bar(n,o,h,l,c):
    return SimpleNamespace(t=T+timedelta(minutes=15*n),o=o,h=h,l=l,c=c)
def signal():
    return dict(side="LONG",score="65",signal_candle_utc=(T-timedelta(minutes=15)).isoformat(),
                b_accepted="1",c_accepted="0",stop="90")
class Paper2080Tests(unittest.TestCase):
    def test_independent_variant_signal(self):
        p=add_signals({},[signal()])
        self.assertEqual(len(p),1)
        self.assertTrue(next(iter(p)).startswith("B|"))
    def test_20pct_then_80pct(self):
        p=add_signals({},[signal()])
        update(p,[bar(0,100,109,95,105),bar(1,108,124,101,122)],T+timedelta(minutes=30))
        x=next(iter(p.values()))
        self.assertEqual(x["status"],"CLOSED")
        self.assertIn("TP1_20PCT",x["events"])
        self.assertIn("TP3_REST",x["events"])
        self.assertAlmostEqual(float(x["net_R"]),1.9)
    def test_stop_priority(self):
        p=add_signals({},[signal()])
        update(p,[bar(0,100,124,89,100)],T+timedelta(minutes=15))
        x=next(iter(p.values()))
        self.assertEqual(x["status"],"CLOSED")
        self.assertEqual(x["events"],"STOP")
    def test_no_unclosed_bar(self):
        p=add_signals({},[signal()])
        update(p,[bar(0,100,124,95,110)],T+timedelta(minutes=5))
        self.assertEqual(next(iter(p.values()))["status"],"AWAIT_ENTRY")
if __name__=="__main__":unittest.main()
