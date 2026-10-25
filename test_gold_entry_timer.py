import unittest
from datetime import datetime,timedelta,timezone
from gold_entry_timer import Candle,assess_entry

T=datetime(2026,10,26,8,15,tzinfo=timezone.utc)
def bar(mins,close,high=101,low=99):
    return Candle(T+timedelta(minutes=mins),100,high,low,close)
def run(bars,mins=10,**kw):
    p=dict(setup_close_utc=T,side="LONG",trigger=100.5,invalid_level=98,
           five_minute_bars=bars,now_utc=T+timedelta(minutes=mins))
    p.update(kw)
    return assess_entry(**p)
class EntryTimerTests(unittest.TestCase):
    def test_closed_confirmation(self):
        self.assertEqual(run([bar(0,101)],5)["status"],"CONFIRMED")
    def test_no_incomplete_candle(self):
        self.assertEqual(run([bar(5,101)],8)["status"],"WAITING")
    def test_high_wick_not_enough(self):
        self.assertEqual(run([bar(0,100,high=110)],5)["status"],"WAITING")
    def test_expiration(self):
        self.assertEqual(run([],30)["status"],"EXPIRED")
    def test_invalidation(self):
        self.assertEqual(run([bar(0,97)],5)["status"],"INVALID")
    def test_no_pre_setup_candles(self):
        self.assertEqual(run([bar(-5,102)],5)["status"],"WAITING")
    def test_short(self):
        self.assertEqual(run([bar(0,98)],5,side="SHORT",trigger=99,invalid_level=102)["status"],"CONFIRMED")
    def test_invalid_timezone(self):
        self.assertEqual(run([],setup_close_utc=T.replace(tzinfo=None))["status"],"INVALID")
    def test_no_lookahead(self):
        self.assertEqual(run([bar(0,101),bar(5,102)],4)["status"],"WAITING")
if __name__=="__main__":unittest.main()
