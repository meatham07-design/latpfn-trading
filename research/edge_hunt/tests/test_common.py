"""Smoke tests for common.py: loaders, fee model, evaluate(), walk_forward(), record_to_lab()."""
import sys, math
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C


def toy_trades():
    t0 = pd.Timestamp("2026-03-01", tz="UTC")
    rows = []
    # 9 trades over 90 days, alternating outcomes; crypto trades use fee model
    for i in range(9):
        et = t0 + pd.Timedelta(days=10 * i)
        px = 100.0
        exit_px = px * (1.02 if i % 3 != 2 else 0.99)
        rows.append(C.crypto_trade(et, et + pd.Timedelta(hours=6), +1, px, exit_px, 10, "BTC"))
    # one CME trade: MNQ long 2 contracts, +10 pts = 2*2*10 = $40 gross, fee 2*2.24
    rows.append(C.cme_trade(t0 + pd.Timedelta(days=45), t0 + pd.Timedelta(days=45, hours=2),
                            +1, 20000.0, 20010.0, 2, "MNQ=F"))
    return pd.DataFrame(rows)


def test_fees():
    assert math.isclose(C.hl_fee(10_000, maker=False), 4.5)
    assert math.isclose(C.hl_fee(10_000, maker=True), 1.5)
    assert C.cme_fee("MNQ") == 2.24 and C.cme_fee("yf_ES_F") == 6.80 and C.cme_fee("GC=F", 2) == 28.0
    assert C.cme_multiplier("MYM") == 0.5 and C.is_cme("BTC") is False


def test_evaluate_toy():
    tr = toy_trades()
    r = C.evaluate(tr)
    assert r["n"] == 10
    # crypto pnl check: 6 winners +20 gross each, 3 losers -10 gross each
    cme = tr.iloc[-1]
    exp_gross = 6 * 20 + 3 * (-10) + 40
    assert math.isclose(r["gross"], exp_gross), r["gross"]
    assert math.isclose(r["net"], exp_gross - tr["fee_usd"].sum())
    assert len(r["folds"]) == 3 and math.isclose(sum(r["folds"]), r["net"])
    assert 0 < r["wr"] < 1 and r["pf"] > 1 and r["max_dd"] > 0
    assert r["net_bps"] == r["net"] / tr["notional_usd"].sum() * 1e4
    assert C.evaluate(tr.iloc[:0])["n"] == 0
    # short-side sign check
    s = pd.DataFrame([C.crypto_trade("2026-01-01", "2026-01-02", -1, 100, 90, 1, "ETH")])
    assert math.isclose(C.evaluate(s)["gross"], 10.0)


def test_walk_forward():
    idx = pd.date_range("2026-01-01", "2026-03-31", freq="1h", tz="UTC")

    def run_fn(p, start, end):
        rows = []
        for t in idx[(idx >= start) & (idx < end)][::24 * 3]:
            edge = p["k"] * 0.5 - 0.5  # k=2 profitable, k=0 losing
            rows.append(C.crypto_trade(t, t + pd.Timedelta(hours=1), 1, 100, 100 + edge, 10, "BTC"))
        return pd.DataFrame(rows)

    best, oos, table = C.walk_forward([{"k": 0}, {"k": 1}, {"k": 2}], run_fn, (idx[0], idx[-1]))
    assert best == {"k": 2}
    assert len(table) == 3 and table["selected"].sum() == 1
    res = C.oos_result(oos, (idx[0], idx[-1]))
    assert res["fold_n"][0] == 0 and res["fold_n"][1] > 0 and res["fold_n"][2] > 0
    assert res["net"] > 0


def test_loaders():
    coins = C.list_hl_coins()
    assert "BTC" in coins
    for iv in C.HL_INTERVALS:
        df = C.hl_candles("BTC", iv)
        assert list(df.columns) == ["open", "high", "low", "close", "volume", "trades"]
        assert df.index.tz is not None and df.index.name == "time" and df.index.is_monotonic_increasing
    f = C.hl_funding("BTC")
    assert {"fundingRate", "premium"} <= set(f.columns) and f.index.tz is not None
    u = C.hl_universe()
    assert {"coin", "dayNtlVlm", "openInterest", "funding", "premium"} <= set(u.columns)
    for sym in ("MNQ=F", "^VIX", "BTC-USD"):
        df = C.yf_bars(sym, "1h")
        assert list(df.columns) == ["open", "high", "low", "close", "volume"] and df.index.tz is not None
    assert len(C.yf_bars("ES=F", "5m")) > 1000
    # next_bar_open must return the NEXT bar's open (no look-ahead)
    b = C.hl_candles("BTC", "1h")
    nb = C.next_bar_open(b, b.index[:3])
    assert b["close"].notna().all() and f["fundingRate"].notna().all()
    assert nb.iloc[0] == b["open"].iloc[1] and nb.iloc[2] == b["open"].iloc[3]


def test_record_to_lab():
    r = C.evaluate(toy_trades())
    rid = C.record_to_lab("smoke_test", "toy", "BTC", "1h", {"k": 1}, r,
                          period=("2026-03-01", "2026-06-01"), source=__file__, notes="smoke test - ignore")
    assert isinstance(rid, int) and rid > 0


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn(); print("ok", name)
