import unittest
from .decision import decide, WEIGHTS
from .indicators import ema, wilder
from .structure import analyze
from .calendar_gate import evaluate_calendar
from .runner import cycle
from unittest.mock import patch

def sample(side="BUY"):
    from .decision import REQUIRED
    s=dict.fromkeys(REQUIRED,True)
    s.update(side=side,h4=side,h1=side,m15=side,m5=side,
             points=dict(WEIGHTS),entry=3500,stop=3495 if side=="BUY" else 3505,
             target=3515 if side=="BUY" else 3485,cost_per_ounce=.2,
             equity_usd=10000,daily_planned_risk_usd=0,
             open_positions=0,loss_streak=0)
    return s

class DecisionTests(unittest.TestCase):
    def test_both_directions(self):
        for side in ("BUY","SELL"):
            d=decide(sample(side))
            self.assertEqual(d["signal"],side)
            self.assertEqual(d["mode"],"PAPER")
            self.assertAlmostEqual(d["planned_risk_usd"],50)
    def test_score_79(self):
        s=sample()
        s["points"]["structure"]=0
        s["points"]["trend"]-=1
        self.assertEqual(decide(s)["signal"],"NO TRADE")
    def test_score_80(self):
        s=sample()
        s["points"]["structure"]=0
        self.assertEqual(decide(s)["signal"],"BUY")
    def test_each_hard_gate(self):
        from .decision import REQUIRED
        for k in REQUIRED:
            with self.subTest(k=k):
                s=sample()
                s[k]=False
                self.assertEqual(decide(s)["signal"],"NO TRADE")
    def test_conflict(self):
        s=sample()
        s["h1"]="SELL"
        self.assertEqual(decide(s)["signal"],"NO TRADE")
    def test_rr_after_cost(self):
        s=sample()
        s["target"]=3510
        self.assertEqual(decide(s)["signal"],"NO TRADE")
    def test_risk_limits(self):
        for k,v in (("loss_streak",3),("open_positions",1),("daily_planned_risk_usd",150)):
            s=sample()
            s[k]=v
            self.assertEqual(decide(s)["signal"],"NO TRADE")
        s=sample()
        s["daily_planned_risk_usd"]=140
        self.assertAlmostEqual(decide(s)["planned_risk_usd"],10)
    def test_nonfinite(self):
        s=sample()
        s["entry"]=float("nan")
        self.assertEqual(decide(s)["signal"],"NO TRADE")

class AnalysisTests(unittest.TestCase):
    def test_constant_indicators(self):
        self.assertEqual(ema([5]*210,200),5)
        self.assertEqual(wilder([5]*20),5)
    def test_open_candle(self):
        rows=[dict(timestamp=i,open=5,high=6,low=4,close=5,closed=True) for i in range(10)]
        rows[-1]["closed"]=False
        with self.assertRaises(ValueError):
            analyze(rows)
    def test_calendar_fail_closed(self):
        d=evaluate_calendar(1795700000,{}, {})
        self.assertFalse(d["news_clear"])
        self.assertFalse(d["session_clear"])
    def test_runner_default_off(self):
        with patch.dict("os.environ",{"DAYTRADER_V1_ENABLED":"0"}):
            d=cycle(None,1795700000,{}, {}, {}, {},10000,0,0)
        self.assertEqual(d["reason"],"DISABLED")

if __name__=="__main__":
    unittest.main()
