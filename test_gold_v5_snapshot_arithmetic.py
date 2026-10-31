"""Synthetic regression tests for Gold V5 indicator/snapshot arithmetic.
No network access, no modification of live signals or paper records.
These tests validate calculation invariants; they do NOT prove the full
forward observer will create a snapshot for a new real market signal.
"""
import math
import unittest
from datetime import datetime, timedelta, timezone

def ema(values, length):
    k=2/(length+1)
    out=[values[0]]
    for value in values[1:]:
        out.append(value*k+out[-1]*(1-k))
    return out

def atr14(bars):
    tr=[bars[0][1]-bars[0][2]]
    for i in range(1,len(bars)):
        _,high,low,_=bars[i]
        previous_close=bars[i-1][3]
        tr.append(max(high-low,abs(high-previous_close),abs(low-previous_close)))
    out=[None]*len(bars)
    out[13]=sum(tr[:14])/14
    for i in range(14,len(bars)):
        out[i]=(out[i-1]*13+tr[i])/14
    return out

def diagnostic_candle(open_,high,low,close):
    if not low<=min(open_,close)<=max(open_,close)<=high:
        raise ValueError("Invalid OHLC")
    return {"body":round(abs(close-open_),5),
            "upper_wick":round(high-max(open_,close),5),
            "lower_wick":round(min(open_,close)-low,5)}

class GoldV5SnapshotArithmetic(unittest.TestCase):
    def test_flat_ema(self):
        for period in (20,50):
            self.assertTrue(all(v==4000 for v in ema([4000.0]*80,period)))
    def test_ema_rising_vs_falling(self):
        rising=ema([3900+i for i in range(90)],20)
        falling=ema([4000-i for i in range(90)],20)
        self.assertGreater(rising[-1],rising[-2])
        self.assertLess(falling[-1],falling[-2])
    def test_constant_range_atr(self):
        bars=[(4000.0,4001.0,3999.0,4000.0)]*60
        a=atr14(bars)
        self.assertIsNone(a[12])
        self.assertAlmostEqual(a[13],2.0)
        self.assertAlmostEqual(a[-1],2.0)
        self.assertAlmostEqual(1.5*a[-1],3.0)
    def test_gap_true_range(self):
        bars=[(4000.0,4001.0,3999.0,4000.0)]*14
        bars.append((4010.0,4012.0,4009.0,4011.0))
        a=atr14(bars)
        self.assertAlmostEqual(a[-1],(2*13+12)/14)
    def test_bull_candle_wicks(self):
        self.assertEqual(diagnostic_candle(4000,4008,3997,4005),
                         {"body":5,"upper_wick":3,"lower_wick":3})
    def test_bear_candle_wicks(self):
        self.assertEqual(diagnostic_candle(4005,4008,3997,4000),
                         {"body":5,"upper_wick":3,"lower_wick":3})
    def test_invalid_candle_fails(self):
        with self.assertRaises(ValueError):
            diagnostic_candle(4005,4002,3999,4000)
    def test_decision_timestamp(self):
        candle=datetime(2026,10,31,9,0,tzinfo=timezone.utc)
        decision=candle+timedelta(minutes=15)
        self.assertEqual((decision-candle).total_seconds(),900)

if __name__=="__main__":
    unittest.main()
