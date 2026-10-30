import unittest
from datetime import datetime,timezone,timedelta
from gold_v5_risk_gate import risk_gate
T=datetime(2026,10,30,12,0,tzinfo=timezone.utc)
def closed(r,t=T):
 return {"cohort":"FORWARD","status":"CLOSED_PAPER","exit_utc":t.isoformat(),"net_R":str(r)}
class GateTests(unittest.TestCase):
 def test_empty(self):self.assertEqual(risk_gate([],T)["decision"],"ALLOW")
 def test_backfill_ignored(self):
  x=closed(-10);x["cohort"]="INITIAL_BACKFILL"
  self.assertEqual(risk_gate([x],T)["decision"],"ALLOW")
 def test_daily_loss(self):self.assertIn("DAILY_LOSS_LIMIT",risk_gate([closed(-1),closed(-1)],T)["reasons"])
 def test_streak(self):self.assertIn("LOSS_STREAK_LIMIT",risk_gate([closed(-0.5)]*3,T)["reasons"])
 def test_drawdown(self):self.assertIn("DRAWDOWN_LIMIT",risk_gate([closed(-4),closed(-3)],T)["reasons"])
 def test_open_blocks(self):self.assertIn("EXISTING_POSITION",risk_gate([{"cohort":"FORWARD","status":"PENDING_ENTRY"}],T)["reasons"])
 def test_unresolved_blocks(self):self.assertIn("UNRESOLVED_DATA_GAP",risk_gate([{"cohort":"FORWARD","status":"UNRESOLVED_DATA_GAP"}],T)["reasons"])
 def test_success(self):self.assertEqual(risk_gate([closed(1.9)],T)["decision"],"ALLOW")
if __name__=="__main__":unittest.main()
