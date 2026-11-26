"""Paper trade journal. No simulated fills are invented here.
A separate execution simulator must supply verified paper fills and costs.
SQLite triggers prevent ordinary updates/deletes, not privileged tampering.
One persistent database per paper account, all monetary amounts in USD.
"""
import json
from math import isfinite

def positive(x):
    return type(x) in (int,float) and isfinite(x) and x>0

def nonnegative(x):
    return type(x) in (int,float) and isfinite(x) and x>=0

class Journal:
    def __init__(self, store):
        self.store=store
        with store.transaction() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS paper_entries(
                zone_id TEXT PRIMARY KEY REFERENCES signals(zone_id),
                filled_at INTEGER NOT NULL, entry REAL NOT NULL,
                ounces REAL NOT NULL, risk_usd REAL NOT NULL,
                session TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS paper_exits(
                zone_id TEXT PRIMARY KEY REFERENCES paper_entries(zone_id),
                filled_at INTEGER NOT NULL, exit_price REAL NOT NULL,
                costs REAL NOT NULL, pnl REAL NOT NULL,
                r_multiple REAL NOT NULL, reason TEXT NOT NULL)""")
            for table in ("paper_entries","paper_exits"):
                for action in ("UPDATE","DELETE"):
                    db.execute(f"""CREATE TRIGGER IF NOT EXISTS {table}_no_{action.lower()}
                    BEFORE {action} ON {table} BEGIN
                    SELECT RAISE(ABORT,'append-only journal'); END""")

    def enter(self, zone_id, filled_at, price, ounces, cost_budget_per_ounce, session):
        if type(filled_at) is not int or not positive(price) or not positive(ounces) or not nonnegative(cost_budget_per_ounce):
            raise ValueError("invalid paper fill")
        if session not in ("London","New York"):
            raise ValueError("invalid session")
        with self.store.transaction() as db:
            row=db.execute("SELECT payload FROM signals WHERE zone_id=?",(zone_id,)).fetchone()
            if not row:
                raise ValueError("missing reserved signal")
            d=json.loads(row[0])
            if d.get("mode")!="PAPER" or d.get("signal") not in ("BUY","SELL"):
                raise ValueError("invalid signal")
            if not d["timestamp"]<=filled_at<=d["valid_until"]:
                raise ValueError("expired signal")
            if not (d["stop"]<price<d["target"] if d["signal"]=="BUY" else d["target"]<price<d["stop"]):
                raise ValueError("invalid fill geometry")
            risk=(abs(price-d["stop"])+cost_budget_per_ounce)*ounces
            reward=(abs(d["target"]-price)-cost_budget_per_ounce)*ounces
            if not positive(risk) or reward/risk<2 or risk>d["planned_risk_usd"]+1e-9 or ounces>d["max_ounces"]+1e-9:
                raise ValueError("fill violates risk or CRV")
            if db.execute("SELECT 1 FROM paper_entries e LEFT JOIN paper_exits x USING(zone_id) WHERE x.zone_id IS NULL LIMIT 1").fetchone():
                raise ValueError("paper position already open")
            db.execute("INSERT INTO paper_entries VALUES(?,?,?,?,?,?)",
                       (zone_id,filled_at,price,ounces,risk,session))

    def exit(self, zone_id, filled_at, price, costs, reason):
        if type(filled_at) is not int or not positive(price) or not nonnegative(costs):
            raise ValueError("invalid paper exit")
        if reason not in ("STOP","TARGET","SESSION_CLOSE","MANUAL_PAPER"):
            raise ValueError("invalid exit reason")
        with self.store.transaction() as db:
            row=db.execute("""SELECT e.filled_at,e.entry,e.ounces,e.risk_usd,s.payload
                FROM paper_entries e JOIN signals s USING(zone_id) WHERE e.zone_id=?""",(zone_id,)).fetchone()
            if not row or filled_at<row[0]:
                raise ValueError("missing entry or invalid exit time")
            _,entry,ounces,risk,payload=row
            side=json.loads(payload)["signal"]
            pnl=(price-entry)*(1 if side=="BUY" else -1)*ounces-costs
            if not isfinite(pnl):
                raise ValueError("invalid PnL")
            db.execute("INSERT INTO paper_exits VALUES(?,?,?,?,?,?,?)",
                       (zone_id,filled_at,price,costs,pnl,pnl/risk,reason))

    def report(self, initial_equity):
        if not positive(initial_equity):
            raise ValueError("invalid initial equity")
        with self.store.transaction() as db:
            signals=db.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
            entries=db.execute("SELECT COUNT(*) FROM paper_entries").fetchone()[0]
            rows=db.execute("""SELECT x.pnl,x.r_multiple,x.costs,e.session,s.payload
                FROM paper_exits x JOIN paper_entries e USING(zone_id)
                JOIN signals s USING(zone_id) ORDER BY x.filled_at,x.zone_id""").fetchall()
        def metrics(items):
            n=len(items)
            wins=sum(r[0]>0 for r in items)
            losses=sum(r[0]<0 for r in items)
            gross_profit=sum(r[0] for r in items if r[0]>0)
            gross_loss=-sum(r[0] for r in items if r[0]<0)
            return dict(closed=n,wins=wins,losses=losses,breakeven=n-wins-losses,
                        win_rate=wins/n if n else None,net_pnl=sum(r[0] for r in items),
                        costs=sum(r[2] for r in items),
                        profit_factor=gross_profit/gross_loss if gross_loss else None,
                        profit_factor_status="defined" if gross_loss else "no losses",
                        expectancy_r=sum(r[1] for r in items)/n if n else None,
                        average_planned_rr=sum(json.loads(r[4])["net_rr"] for r in items)/n if n else None)
        equity=peak=initial_equity
        drawdown=drawdown_pct=0.0
        for r in rows:
            equity+=r[0]
            peak=max(peak,equity)
            drawdown=max(drawdown,peak-equity)
            drawdown_pct=max(drawdown_pct,(peak-equity)/peak)
        out=metrics(rows)
        out.update(mode="PAPER",signals=signals,entries=entries,open_positions=entries-len(rows),
                   realized_drawdown_usd=drawdown,realized_drawdown_fraction=drawdown_pct,
                   ending_realized_equity=equity,
                   by_session={s:metrics([r for r in rows if r[3]==s]) for s in ("London","New York")},
                   by_score={str(lo):metrics([r for r in rows if lo<=json.loads(r[4])["score"]<hi])
                             for lo,hi in ((80,90),(90,101))})
        return out
