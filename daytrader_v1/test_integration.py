import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from .zone_store import ZoneStore
from .journal import Journal
from .paper_execution import PaperExecution
from .runner import risk_snapshot
from .telegram import dispatch

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"paper.sqlite"
        self.store=ZoneStore(self.path)
        self.journal=Journal(self.store)
        self.now=1795700100
        self.zone=dict(side="BUY",start=3480,end=3520,lower=3495.28,upper=3500,
                       start_time=self.now-3600,end_time=self.now-1800,confirmed_at=self.now-900)
        self.key=self.store.register(self.zone,self.now)
        self.assertTrue(self.store.update(self.key,"CANDIDATE",self.now))
        self.signal=dict(mode="PAPER",instrument="XAUUSD",signal="BUY",
                         timestamp=self.now,valid_until=self.now+60,score=90,net_rr=2.8,
                         entry=3500,stop=3495,target=3515,max_ounces=9,
                         planned_risk_usd=50,zone=self.zone)
    def reserve(self):
        self.assertTrue(self.store.reserve_signal(self.key,self.now,self.signal,self.now))
    def quote(self,t,bid,ask):
        return dict(verified=True,instrument="XAUUSD",timestamp=t,bid=bid,ask=ask)
    def fill(self):
        self.reserve()
        engine=PaperExecution(self.journal)
        risk=risk_snapshot(self.store,self.now,10000)
        gates=dict(news_clear=True,session_clear=True,as_of=self.now,session="London")
        self.assertEqual(engine.enter(self.key,self.quote(self.now,3499.8,3500),
                         self.now,gates,risk,.2,0),"PAPER_FILLED")
        return engine
    def test_restart_dedup(self):
        self.reserve()
        reopened=ZoneStore(self.path)
        self.assertEqual(reopened.register(self.zone,self.now),self.key)
        self.assertEqual(reopened.active(),[])
        self.assertFalse(reopened.reserve_signal(self.key,self.now,self.signal,self.now))
    def test_expired_signal(self):
        self.assertFalse(self.store.reserve_signal(self.key,self.now,self.signal,self.now+61))
    def test_target_and_journal(self):
        engine=self.fill()
        t=self.now+10
        self.assertEqual(engine.monitor(self.quote(t,3516,3516.2),t,{},.2,0),"TARGET")
        report=self.journal.report(10000)
        self.assertEqual(report["wins"],1)
        self.assertEqual(report["open_positions"],0)
        self.assertAlmostEqual(report["net_pnl"],133.2)
    def test_stop_gap(self):
        engine=self.fill()
        t=self.now+10
        self.assertEqual(engine.monitor(self.quote(t,3493,3493.2),t,{},.2,0),"STOP")
        report=self.journal.report(10000)
        self.assertEqual(report["losses"],1)
        self.assertAlmostEqual(report["net_pnl"],-64.8)
        self.assertAlmostEqual(report["realized_drawdown_usd"],64.8)
    def test_session_close(self):
        engine=self.fill()
        t=self.now+10
        self.assertEqual(engine.monitor(self.quote(t,3501,3501.2),t,
                         dict(verified=True,flatten_at=t),.2,0),"SESSION_CLOSE")
    def test_telegram_off(self):
        self.reserve()
        with patch.dict("os.environ",{"DAYTRADER_V1_TELEGRAM_ENABLED":"0"}):
            self.assertEqual(dispatch(self.store,self.key),"DISABLED")

if __name__=="__main__":
    unittest.main()
