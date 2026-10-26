import unittest
from datetime import datetime,timedelta,timezone
from gold_forward_bc_telegram import candidates,message
T=datetime(2026,10,26,8,0,tzinfo=timezone.utc)
def row(b="1",c="0",closed=None):
    return dict(signal_candle_utc=(T-timedelta(minutes=15)).isoformat(),
      closed_at_utc=(closed or T).isoformat(),side="LONG",score="65",
      b_accepted=b,c_accepted=c,bar_close="4010",stop="4000",
      tp1="4015",tp2="4020",tp3="4030")
class TelegramGoldTests(unittest.TestCase):
    def test_b_accepted(self):self.assertEqual(len(candidates([row()],set(),T)),1)
    def test_c_only_accepted(self):self.assertEqual(len(candidates([row("0","1")],set(),T)),1)
    def test_unaccepted_not_sent(self):self.assertEqual(candidates([row("0","0")],set(),T),[])
    def test_repeat_suppressed(self):
        seen=set();candidates([row()],seen,T)
        self.assertEqual(candidates([row()],seen,T),[])
    def test_old_signal_not_sent(self):self.assertEqual(candidates([row(closed=T-timedelta(hours=3))],set(),T),[])
    def test_message_demo_notice(self):
        msg=message(row());self.assertIn("TESTSIGNAL",msg);self.assertIn("keine Order",msg)
if __name__=="__main__":unittest.main()
