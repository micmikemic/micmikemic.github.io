"""
Strategy 2 — Solar cannibalisation spread (short midday, long evening).

The structural trade behind the "duck curve": every additional GW of
solar depresses the 11:00-15:00 day-ahead block and (relatively) lifts
the 18:00-21:00 evening ramp. A trader without a battery can express
this financially: in the day-ahead auction (or via shaped futures),
SELL the midday block and BUY the evening block, same day, same MW.

P&L per MW per day = mean(DA evening hours) - mean(DA midday hours)
                     - transaction costs.

Why this is a real edge and not a backtest artefact:
  - it is the same spread a battery monetises, and battery fleets are
    not yet large enough in DE/CZ to close it (watch that for decay!);
  - it has an identifiable counterparty: must-run solar selling at
    any price midday, inflexible demand buying the evening ramp;
  - it is strongly seasonal (solar) -> a calendar filter is decision-
    time safe (no information leakage).

We report the unconditional spread, a March-October seasonal variant,
and year-by-year evolution so the growth/decay of the edge is visible.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

MIDDAY = range(11, 15)    # short leg, local hours 11:00-14:59
EVENING = range(18, 21)   # long leg, local hours 18:00-20:59
COST_EUR_MWH = 0.30       # exchange fees + slippage per MWh per leg


def daily_spread(prices: pd.Series) -> pd.DataFrame:
    """Per-day evening-minus-midday spread [EUR/MWh] from hourly DA prices."""
    df = prices.dropna().to_frame("p")
    df["hour"] = df.index.hour
    df["date"] = df.index.normalize()
    mid = df[df.hour.isin(MIDDAY)].groupby("date")["p"].mean()
    eve = df[df.hour.isin(EVENING)].groupby("date")["p"].mean()
    out = pd.DataFrame({"midday": mid, "evening": eve}).dropna()
    out["spread"] = out.evening - out.midday
    out["pnl"] = out.spread - 2 * COST_EUR_MWH
    return out


def summary(spread: pd.DataFrame) -> pd.DataFrame:
    """Year-by-year economics of the spread, all-year vs solar season."""
    rows = []
    for year, g in spread.groupby(spread.index.year):
        season = g[g.index.month.isin(range(3, 11))]
        for label, d in [("all year", g), ("Mar-Oct", season)]:
            n = len(d)
            mu, sd = d.pnl.mean(), d.pnl.std()
            rows.append({
                "year": year, "variant": label, "days": n,
                "avg_pnl_eur_mwh": round(mu, 2),
                "win_rate": round((d.pnl > 0).mean(), 3),
                "t_stat": round(mu / (sd / np.sqrt(n)), 1) if n > 2 else np.nan,
                "ann_sharpe": round(mu / sd * np.sqrt(365), 2) if sd > 0 else np.nan,
                "worst_day": round(d.pnl.min(), 1),
            })
    return pd.DataFrame(rows).set_index(["year", "variant"])


def negative_price_stats(prices: pd.Series) -> pd.DataFrame:
    """Negative-price hours per year — context for how fast solar is
    cannibalising itself (and feeding flexible-asset edges)."""
    p = prices.dropna()
    g = p.groupby(p.index.year)
    return pd.DataFrame({
        "neg_hours": g.apply(lambda s: int((s < 0).sum())),
        "pct_negative": (g.apply(lambda s: (s < 0).mean()) * 100).round(2),
        "min_price": g.min().round(1),
        "mean_price": g.mean().round(1),
    })


if __name__ == "__main__":
    from power_api import cached_history

    out = Path(__file__).parent.parent / "results"
    out.mkdir(exist_ok=True)
    for bzn in ["DE-LU", "CZ"]:
        prices = cached_history(bzn)
        sp = daily_spread(prices)
        sp.to_csv(out / f"solar_spread_daily_{bzn}.csv")
        print(f"\n=== Solar cannibalisation spread, {bzn} "
              f"(sell 11-15h / buy 18-21h, {COST_EUR_MWH} EUR/MWh/leg cost) ===")
        print(summary(sp).to_string())
        print(f"\n--- negative price hours, {bzn} ---")
        print(negative_price_stats(prices).to_string())
