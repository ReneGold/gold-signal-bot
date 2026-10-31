import unittest
from gold_v5_forward_audit import audit

class ForwardAuditTests(unittest.TestCase):
    def test_excludes_backfill_and_open(self):
        result = audit([
            {"cohort":"INITIAL_BACKFILL","status":"CLOSED","net_R":"100"},
            {"cohort":"FORWARD","status":"OPEN","net_R":"100"},
            {"cohort":"FORWARD","status":"CLOSED","net_R":"1.5","trade_id":"a","signal_time_utc":"2026-10-30T00:00:00Z"},
            {"cohort":"FORWARD","status":"CLOSED","net_R":"-1","trade_id":"b","signal_time_utc":"2026-10-31T00:00:00Z"}
        ])
        self.assertEqual(result["sample_size"], 2)
        self.assertEqual(result["base"]["net_R"], 0.5)
        self.assertEqual(result["base"]["max_closed_drawdown_R"], 1)
        self.assertEqual(result["cost_stress"]["0.25"]["net_R"], 0)
        self.assertEqual(result["excluded"]["backfill_or_recovered"], 1)
        self.assertEqual(result["excluded"]["not_closed"], 1)

    def test_invalid_and_duplicate_not_counted(self):
        result = audit([
            {"cohort":"FORWARD","status":"CLOSED","net_R":"1","trade_id":"one"},
            {"cohort":"FORWARD","status":"CLOSED","net_R":"2","trade_id":"one"},
            {"cohort":"FORWARD","status":"CLOSED","net_R":"nan","trade_id":"two"}
        ])
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(len(result["row_errors"]), 2)

    def test_actual_ledger_format(self):
        result = audit([{"cohort":"FORWARD","status":"CLOSED_PAPER","net_R":"1.90306","signal_utc":"2026-10-29T23:00:00+00:00","exit_utc":"2026-10-30T01:00:00+00:00","phase":"RANGE_OR_WEAK"}])
        self.assertEqual(result["sample_size"], 1)
        self.assertEqual(result["base"]["net_R"], 1.90306)
        self.assertEqual(result["regime_breakdown"]["RANGE_OR_WEAK"]["n"], 1)

    def test_empty_sample_is_not_success(self):
        result = audit([])
        self.assertEqual(result["sample_size"], 0)
        self.assertIsNone(result["base"]["win_rate_pct"])
        self.assertIsNone(result["base"]["profit_factor"])

if __name__ == "__main__":
    unittest.main()
