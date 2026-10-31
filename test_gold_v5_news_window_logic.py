import unittest
from gold_v5_news_window_logic import matching_events

FOMC=[
 {"category":"FOMC_STATEMENT","release_utc":"2026-12-09T19:00:00+00:00"},
 {"category":"FOMC_PRESS_CONFERENCE","release_utc":"2026-12-09T19:30:00+00:00"}
]
class WindowLogicTests(unittest.TestCase):
 def test_overlap_is_one_signal(self):
  for minutes in (15,30,60):
   matches=matching_events("2026-12-09T19:15:00+00:00",FOMC,minutes)
   self.assertEqual(len(matches),2)
   self.assertEqual(int(bool(matches)),1)
 def test_boundary_inclusive(self):
  self.assertEqual(len(matching_events("2026-12-09T18:30:00+00:00",FOMC,30)),1)
 def test_outside(self):
  self.assertEqual(matching_events("2026-12-09T17:00:00+00:00",FOMC,60),[])
 def test_requires_timezone(self):
  with self.assertRaises(ValueError):
   matching_events("2026-12-09T19:00:00",FOMC,30)
if __name__=="__main__":unittest.main()
