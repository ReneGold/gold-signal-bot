import unittest
from gold_time_machine import Bar,analyze,replay

class TimeMachineTests(unittest.TestCase):
    def setUp(self):
        self.bars=[Bar(4000+i*0.01,4002+i*0.01,3998+i*0.01,4001+i*0.01) for i in range(150)]
    def test_replay_target(self):
        b=[Bar(100,100,100,100),Bar(100,104,99,103),Bar(100,105,99,104)]
        r,out=replay(b,0,1,2,target_r=1,horizon=1,cost_per_oz=0)
        self.assertEqual(out,"TARGET");self.assertEqual(r,1)
    def test_stop_first_when_both_hit(self):
        b=[Bar(100,100,100,100),Bar(100,104,96,100)]
        _,out=replay(b,0,1,2,target_r=1,horizon=1)
        self.assertEqual(out,"STOP")
    def test_no_future_candles(self):
        with self.assertRaises(ValueError):replay(self.bars,149,1,2)
    def test_analog_history_only(self):
        a=analyze(self.bars,100,1,3,horizon=12)
        changed=self.bars[:101]+[Bar(100000,100000,1,2) for _ in range(49)]
        self.assertEqual(a,analyze(changed,100,1,3,horizon=12))
    def test_insufficient_lookback(self):
        self.assertEqual(analyze(self.bars,4,1,3,horizon=12)["sample_size"],0)
    def test_bad_side(self):
        with self.assertRaises(ValueError):analyze(self.bars,100,0,2)
if __name__=="__main__":unittest.main()
