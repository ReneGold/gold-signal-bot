import unittest
from datetime import datetime,timedelta,timezone
from gold_v4_research_pipeline import evaluate
from gold_entry_timer import Candle as EBar
from gold_time_machine import Bar
T=datetime(2026,10,26,12,15,tzinfo=timezone.utc)
class V4IntegrationTests(unittest.TestCase):
    def inp(self,**kw):
        bs=[EBar(T-timedelta(minutes=15*(100-i)),4000,4005,3995,4000) for i in range(101)]
        x=dict(variant="B",side="LONG",entry=4001,stop=3996,score=65,
             signal_close_utc=T+timedelta(minutes=15),asof_utc=T+timedelta(minutes=20),
             fifteen_bars=bs,signal_index=100,
             five_bars=[EBar(T+timedelta(minutes=15),4001,4004,4000,4003)],
             atr_15m=8,events=[],calendar_verified=True,equity=5000,
             day_realized_pnl=0,quantity_oz=2,open_positions=0,
             position_currency_matches_account=True)
        x.update(kw);return evaluate(**x)
    def test_reject_missing_calendar(self):
        self.assertEqual(self.inp(calendar_verified=False)["status"],"NOT_READY")
    def test_reject_currency_mismatch(self):
        self.assertEqual(self.inp(position_currency_matches_account=False)["status"],"NOT_READY")
    def test_reject_risk(self):
        self.assertEqual(self.inp(quantity_oz=100)["stage"],"RISK")
    def test_reject_score(self):
        self.assertEqual(self.inp(score=50)["status"],"REJECTED")
    def test_timer_waits(self):
        self.assertEqual(self.inp(five_bars=[])["status"],"NOT_READY")
    def test_news_blocks(self):
        from gold_news_volatility_filter import Event
        self.assertEqual(self.inp(events=[Event(T+timedelta(minutes=20),"CPI")])["stage"],"NEWS_VOL")
    def test_integrated_candidate(self):
        r=self.inp()
        self.assertEqual(r["status"],"RESEARCH_CANDIDATE")
        self.assertEqual(len(r["exit_targets"]),3)
if __name__=="__main__":unittest.main()
