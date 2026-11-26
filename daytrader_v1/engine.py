"""Integrated paper-only evaluation. No broker, scheduler or external data calls.
Timestamps: integer UTC epoch seconds, candle close time.
Trusted adapters must attest feed, calendar, session and risk state.
"""
from math import isfinite
from .structure import multi_timeframe
from .pullback import zone, observe
from .smc import analyze_smc
from .indicators import features
from .scoring import score_setup
from .decision import decide

PERIODS = dict(h4=14400,h1=3600,m15=900,m5=300)

def evaluate(frames, context):
    result = dict(instrument="XAUUSD",mode="PAPER",signal="NO TRADE")
    def reject(reason):
        return dict(result,reason=reason)
    try:
        now = context["now"]
        result["timestamp"] = now
        if type(now) is not int or now <= 0:
            return reject("invalid clock")
        for key in ("data_verified","news_clear","spread_clear","session_clear","risk_verified"):
            if context.get(key) is not True:
                return reject(key)
        if context.get("instrument") != "XAUUSD":
            return reject("instrument mismatch")
        for tf, period in PERIODS.items():
            rows = frames[tf]
            if len(rows)<201:
                return reject("insufficient history: "+tf)
            times = [c["timestamp"] for c in rows]
            if any(type(t) is not int or t>now for t in times):
                return reject("invalid candle time: "+tf)
            if not 0<=now-times[-1]<period+60:
                return reject("stale frame: "+tf)
            if any(c.get("closed") is not True for c in rows):
                return reject("open candle: "+tf)
            # Recent active-session bars must be consecutive. Earlier market
            # closures and complete history are verified by the feed adapter.
            if any(b-a!=period for a,b in zip(times[-5:-1],times[-4:])):
                return reject("recent data gap: "+tf)
        if now-frames["m5"][-1]["timestamp"]>60:
            return reject("late M5 evaluation")
        trend = multi_timeframe(frames)
        side = trend["side"]
        result["directions"] = {k:v["direction"] for k,v in trend["frames"].items()}
        if side == "NO TRADE":
            return reject("timeframe conflict")
        z = zone(frames["m15"],side)
        result["zone"] = z
        if not z:
            return reject("no confirmed impulse")
        if frames["m5"][0]["timestamp"] > z["confirmed_at"]:
            return reject("incomplete zone history")
        obs = observe(z,frames["m5"])
        result["observation"] = obs
        f = {tf:features(rows,context.get("session_start"),context.get("volume_kind"))
             for tf,rows in frames.items()}
        smc = analyze_smc(frames["m5"])
        quality = score_setup(side,trend["frames"],f,smc,z,obs)
        result.update(score=quality["score"],points=quality["points"])
        if obs["status"]!="CANDIDATE":
            return reject("pullback: "+obs["status"])
        m = f["m5"]
        if m.get("vwap") is None or m.get("price_action")!=side or m.get("momentum")!=side:
            return reject("missing VWAP or entry confirmation")
        atr = m["atr14"]
        if not atr>0 or not .5<= (m.get("atr_ratio") or 0)<=2.5:
            return reject("volatility")
        buy = side=="BUY"
        bid,ask,cost = (float(context[k]) for k in ("bid","ask","cost_per_ounce"))
        if not all(isfinite(x) for x in (bid,ask,cost)) or not 0<bid<=ask or cost<0:
            return reject("invalid quote or cost")
        quote_time=context["quote_time"]
        if type(quote_time) is not int or not 0<=now-quote_time<=30:
            return reject("stale quote")
        entry=ask if buy else bid
        if abs(entry-m["close"])>.25*atr or ask-bid>.2*atr:
            return reject("spread or entry displacement")
        # Conservative stop behind pullback swing and zone, with ATR buffer.
        recent=[c for c in frames["m5"] if c["timestamp"]>z["confirmed_at"]]
        stop=min(z["lower"],min(float(c["low"]) for c in recent))-.25*atr if buy else max(z["upper"],max(float(c["high"]) for c in recent))+.25*atr
        # First known opposing swing; never invent a target to force CRV.
        opposing=[]
        for tf in ("m5","m15","h1","h4"):
            for swing in trend["frames"][tf]["swing_highs" if buy else "swing_lows"]:
                p=swing["price"]
                if p>entry if buy else p<entry:
                    opposing.append(p)
        if not opposing:
            return reject("no verified target")
        target=min(opposing) if buy else max(opposing)
        if type(context["loss_streak"]) is not int or type(context["open_positions"]) is not int:
            return reject("invalid risk counters")
        # loss_count is total daily losses, not merely consecutive losses.
        if type(context["daily_loss_count"]) is not int or not 0<=context["daily_loss_count"]<3:
            return reject("daily loss limit")
        inputs={k:context[k] for k in ("data_verified","news_clear","spread_clear","session_clear","risk_verified","equity_usd","daily_planned_risk_usd","open_positions","loss_streak")}
        inputs.update(result["directions"])
        inputs.update(side=side,points=quality["points"],entry=entry,stop=stop,target=target,
                      cost_per_ounce=cost,closed_candles=True,pullback_confirmed=True,
                      entry_confirmed=True,not_chasing=True,target_verified=True,stop_verified=True)
        decision=decide(inputs)
        result.update(decision)
        if decision["signal"] in ("BUY","SELL"):
            result.update(valid_until=now+60,reason="all programmed gates passed",
                          cancel_if="quote moves beyond 0.25 ATR, risk/news/session changes or signal expires")
        return result
    except (KeyError,TypeError,ValueError,IndexError,OverflowError,AttributeError) as exc:
        return reject("invalid or missing input: "+type(exc).__name__)
