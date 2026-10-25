import unittest
from datetime import datetime,timedelta,timezone
from gold_v4_market_observer import scan
from gold_entry_timer import Candle
T=datetime(2026,10,26,12,0,tzinfo=timezone.utc)
class MarketObservationTests(unittest.TestCase):
    def setUp(self):
        self.bars=[Candle(T+timedelta(minutes=15*i),4000,4004,3996,4000) for i in range(105)]
        self.five=[Candle(T+timedelta(minutes=15*104+5*i),4000,4004,3996,4002) for i in range(6)]
        self.row=dict(signal_candle_utc=self.bars[-1].t.isoformat(),side="LONG",score="65",
            b_accepted="1",c_accepted="1",bar_close="4000",stop="3995")
    def test_no_signal(self):
        r=dict(self.row,b_accepted="0",c_accepted="0")
        self.assertEqual(scan([r],self.bars,self.five,[8]*105),[])
    def test_missing_candle(self):
        r=dict(self.row,signal_candle_utc=T.isoformat())
        result=scan([r],self.bars,self.five,[8]*105)
        self.assertTrue(all(x["status"]=="NOT_READY" for x in result))
    def test_no_trade_approval_without_calendar_broker(self):
        rows=scan([self.row],self.bars,self.five,[8]*105)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(x["status"]=="NOT_READY" for x in rows))
    def test_calendar_never_approves_without_broker(self):
        from gold_news_volatility_filter import Event
        result=scan([self.row],self.bars,self.five,[8]*105,
            {"verified":False,"status":"UNVERIFIED_FREE_CALENDAR_COVERAGE",
             "events":[Event(T+timedelta(minutes=15*104+20),"US CPI")]})
        self.assertEqual(len(result),2)
        self.assertTrue(all(x["status"]=="NOT_READY" for x in result))
        self.assertTrue(all(x["calendar_verified"] is False for x in result))
    def test_no_5min(self):
        rows=scan([self.row],self.bars,[],[8]*105)
        self.assertTrue(all(x["status"]=="NOT_READY" for x in rows))
if __name__=="__main__":unittest.main()
