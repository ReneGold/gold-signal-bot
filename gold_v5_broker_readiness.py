#!/usr/bin/env python3
"""Gold V5 broker reconciliation readiness report: educational, no execution.
Official public PU Prime reference specs are NOT authenticated account specs.
Fails closed on any lot-size calculation until exact MT4/MT5 symbol spec is
supplied and validated independently. Read-only report; strategy unchanged.
"""
import json,math
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parent
source=root/"gold_v5_forward_ledger.csv"
# Public broker descriptions are references only, never trusted execution input.
reference={
 "provider":"PU Prime public website",
 "symbol":"XAUUSD",
 "contract_ounces_per_lot_reference":100,
 "minimum_lots_reference":0.01,
 "alternative_symbol":"XAUUSD247",
 "alternative_contract_ounces_per_lot_reference":1,
 "alternative_minimum_lots_reference":1,
 "source":"https://de.puprime.com/24-7-gold-trading/",
 "source_note":"Contract/specifications shown in client's MT4/MT5 platform prevail."
}
# No unknown dynamic live quote/FX, lot step or margin silently estimated.
required=["exact_account_type","exact_symbol","contract_size_from_mt5",
          "minimum_volume_from_mt5","volume_step_from_mt5","maximum_volume_from_mt5",
          "tick_size_from_mt5","tick_value_from_mt5","account_currency",
          "live_bid","live_ask","commission_round_turn","margin_requirement",
          "account_fx_conversion_if_needed","market_hours_from_mt5"]
report={
 "generated_utc":datetime.now(timezone.utc).isoformat(),
 "module":"GOLD_V5_BROKER_SPECIFICATION_READINESS",
 "reference_specs":reference,
 "confirmed_account_specs":{},
 "missing_verifications":required,
 "broker_execution_ready":False,
 "lot_size":None,
 "actual_spread":None,
 "status":"BLOCK_BROKER_SIZING_AND_EXECUTION",
 "next_action":"Obtain MT4/MT5 XAUUSD Specification from connected account and typical bid/ask observations. Validate costs and contract math before implementing a paper lot-size calculator.",
 "warnings":[
  "Instrument XAUUSD is not interchangeable with XAUUSD247.",
  "Published standard/prime spreads are indications, not live executable prices.",
  "Equity EUR and XAUUSD tick value USD require an independently sourced currency conversion.",
  "Do not route real orders from this GitHub workflow.",
  "No impact on frozen Gold V5 paper signal calculation or existing TradingView/Telegram."
 ]
}
(root/"gold_v5_broker_readiness.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
