"""No synthetic candles may be invented during 15m-to-H1 aggregation."""
import unittest
from datetime import datetime,timedelta,timezone
from gold_research_derive_h1 import aggregate
UTC=timezone.utc
class H1AggregationTests(unittest.TestCase):
    def setUp(self):
        self.t=datetime(2026,8,3,12,tzinfo=UTC)
    def row(self,n,price):
        return {"timestamp":(self.t+timedelta(minutes=15*n)).isoformat(),
                "open":str(price),"high":str(price+1),"low":str(price-1),"close":str(price+.5)}
    def test_complete_hour(self):
        h,skip=aggregate([self.row(i,100+i) for i in range(4)])
        self.assertEqual(len(h),1)
        self.assertEqual(skip,0)
        self.assertEqual(h[0]["open"],100)
        self.assertEqual(h[0]["high"],104)
        self.assertEqual(h[0]["low"],99)
        self.assertEqual(h[0]["close"],103.5)
    def test_partial_hour_is_not_filled(self):
        h,skip=aggregate([self.row(i,100+i) for i in (0,1,3)])
        self.assertEqual(len(h),0)
        self.assertEqual(skip,1)
    def test_weekend_gap_is_not_filled(self):
        rows=[self.row(i,100+i) for i in range(4)]
        rows += [self.row(i,100+i) for i in range(12,16)]
        h,skip=aggregate(rows)
        self.assertEqual(len(h),2)
        self.assertEqual(skip,0)
    def test_duplicate_candles_rejected(self):
        with self.assertRaises(ValueError):aggregate([self.row(0,100),self.row(0,100)])
if __name__=="__main__":unittest.main()
