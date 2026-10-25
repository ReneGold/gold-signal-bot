import unittest
from gold_exit_planner import Plan,new_position,on_bar

class ExitTests(unittest.TestCase):
    def setUp(self):self.p=Plan(4000,3990,1)
    def bar(self,p,s,lo,hi,op=4000,cl=4000):return on_bar(p,s,open_price=op,high=hi,low=lo,close=cl)
    def test_targets(self):self.assertEqual(self.p.targets,(4007.5,4015.0,4022.5))
    def test_tp1(self):
        s=self.bar(self.p,new_position(self.p),3995,4009)
        self.assertEqual(s["stage"],1);self.assertAlmostEqual(s["remaining"],0.7)
    def test_tp2(self):
        s=self.bar(self.p,new_position(self.p),3995,4016)
        self.assertEqual(s["stage"],2);self.assertAlmostEqual(s["gross_R"],0.675)
    def test_tp3(self):
        s=self.bar(self.p,new_position(self.p),3995,4024)
        self.assertTrue(s["closed"]);self.assertAlmostEqual(s["gross_R"],1.575)
    def test_stop_first_same_candle(self):
        s=self.bar(self.p,new_position(self.p),3988,4030)
        self.assertEqual(s["events"],["STOP"]);self.assertEqual(s["gross_R"],-1)
    def test_breakeven_after_tp1(self):
        s=self.bar(self.p,new_position(self.p),3995,4009)
        s=self.bar(self.p,s,3999,4001)
        self.assertTrue(s["closed"]);self.assertAlmostEqual(s["gross_R"],0.225)
    def test_tp1_stop_after_tp2(self):
        s=self.bar(self.p,new_position(self.p),3995,4016)
        s=self.bar(self.p,s,4007,4010,op=4008,cl=4008)
        self.assertTrue(s["closed"]);self.assertAlmostEqual(s["gross_R"],0.975)
    def test_short(self):
        p=Plan(4000,4010,-1)
        s=self.bar(p,new_position(p),3977,4005)
        self.assertTrue(s["closed"]);self.assertAlmostEqual(s["gross_R"],1.575)
    def test_gap_stop(self):
        s=self.bar(self.p,new_position(self.p),3970,3980,op=3975,cl=3978)
        self.assertAlmostEqual(s["gross_R"],-2.5)
    def test_bad_portions(self):
        with self.assertRaises(ValueError):Plan(4000,3990,1,portions=(.2,.3,.4))
if __name__=="__main__":unittest.main()
