import unittest
from gold_risk_manager import check_trade

class RiskChecks(unittest.TestCase):
    def base(self,**kwargs):
        a=dict(equity=5000,day_realized_pnl=0,entry=4000,stop=3995,
               target=4010,quantity_oz=2,open_positions=0)
        a.update(kwargs)
        return check_trade(**a)
    def test_allow(self): self.assertTrue(self.base()["approved"])
    def test_big_position(self): self.assertFalse(self.base(quantity_oz=10)["approved"])
    def test_low_reward(self): self.assertFalse(self.base(target=4005)["approved"])
    def test_daily_limit(self): self.assertFalse(self.base(day_realized_pnl=-110)["approved"])
    def test_open_position(self): self.assertFalse(self.base(open_positions=1)["approved"])
    def test_invalid_stop(self): self.assertFalse(self.base(stop=4005)["approved"])
    def test_short(self): self.assertTrue(self.base(stop=4005,target=3990)["approved"])
if __name__=="__main__":unittest.main()
