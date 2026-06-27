"""
Strategy 3 — CZ-DE cross-border spread: statistics + mean-reversion tests.

CZ and DE-LU are tightly coupled through flow-based market coupling
(Core FBMC): the hourly day-ahead spread is zero-ish most of the time
and blows out when interconnector capacity binds. Questions:

  1. Descriptive: how often decoupled, in which hours, how fat are the
     tails?  (-> dashboards)
  2. Tradable: does the daily average spread mean-revert *after costs
     and realistic execution timing*?

Two backtest variants are reported side by side:

PAPER (upper bound, NOT tradable)
    Signal: z-score of yesterday's printed daily spread vs trailing 30d.
    P&L:    position x (spread_D - spread_{D-1}).
    Flaw:   "entry" happens at spread_{D-1}, a price that had already
    printed when the signal existed. No instrument lets you transact at
    it. This is the variant that produced the Sharpe ~2.4 — treat it as
    the theoretical ceiling of the signal, nothing more.

TRADABLE (what a desk could actually do with daily auctions)
    Timeline: spread for delivery day D-1 prints ~12:45 two days before
    D. The first auction still open after the signal exists is delivery
    day D (gate 12:00 on D-1). Enter the paired zonal position there —
    you transact AT whatever spread_D clears, you don't choose it —
    and unwind at the D+1 auction.
    P&L:    position(z through D-1) x (spread_{D+1} - spread_D).
    One extra day of lag, entry at market, both legs costed.

Costs: each unit of position change is charged half the round-trip
cost. Base case 2 EUR/MWh RT (CZ futures/auction legs are thin; the
1 EUR/MWh used previously is a best case, so a grid 0.5-4 is reported).

Significance: a stationary block bootstrap (mean block 10 days) gives a
confidence interval for the annualised Sharpe of the tradable variant —
daily spread P&L is fat-tailed and autocorrelated, plain t-stats
overstate certainty.

Even the tradable variant still abstracts from reality: paired zonal
DA positions need a BRP in both zones (or thin PXE/EEX futures whose
basis adds noise), and quoted costs exclude the liquidity hole that
opens exactly when the spread blows out. Numbers below are an upper
bound on a real implementation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

COUPLED_EPS = 0.5         # |spread| below this => zones effectively coupled
Z_ENTRY = 1.5
LOOKBACK_D = 30
RT_COST_BASE = 2.0        # EUR/MWh round trip, base case
RT_COST_GRID = [0.5, 1.0, 2.0, 3.0, 4.0]
BOOT_DRAWS = 2000
BOOT_BLOCK = 10           # mean block length, days


def build_spread(cz: pd.Series, de: pd.Series) -> pd.DataFrame:
    df = pd.concat([cz.rename("CZ"), de.rename("DE")], axis=1).dropna()
    df["spread"] = df.CZ - df.DE
    return df


def descriptive(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(df.index.year)["spread"]
    return pd.DataFrame({
        "mean": g.mean().round(2),
        "std": g.std().round(2),
        "pct_coupled": (g.apply(lambda s: (s.abs() < COUPLED_EPS).mean()) * 100).round(1),
        "p99_abs": g.apply(lambda s: s.abs().quantile(0.99)).round(1),
        "max_abs": g.apply(lambda s: s.abs().max()).round(1),
    })


def hour_profile(df: pd.DataFrame) -> pd.Series:
    return df.groupby(df.index.hour)["spread"].apply(
        lambda s: s.abs().mean()).round(2)


def _signal(daily: pd.Series) -> pd.Series:
    """z-score of the last printed daily spread vs trailing window.
    z_t uses data through delivery day t-1 only."""
    mu = daily.rolling(LOOKBACK_D).mean().shift(1)
    sd = daily.rolling(LOOKBACK_D).std().shift(1)
    z = (daily.shift(1) - mu) / sd
    pos = pd.Series(0.0, index=daily.index)
    pos[z > Z_ENTRY] = -1.0
    pos[z < -Z_ENTRY] = 1.0
    return pos, z


def backtest(df: pd.DataFrame, rt_cost: float, tradable: bool) -> pd.DataFrame:
    """Mean-reversion backtest. tradable=False reproduces the paper
    (untradable) timing; tradable=True adds the extra execution day."""
    daily = df["spread"].resample("1D").mean().dropna()
    pos, z = _signal(daily)
    if tradable:
        # position decided with info through D-1 is filled at auction D
        # and unwound at auction D+1 -> earns the D -> D+1 change
        eff_pos = pos.shift(1)
    else:
        eff_pos = pos
    chg = daily.diff()
    cost = eff_pos.diff().abs().fillna(0) * rt_cost / 2
    pnl = eff_pos * chg - cost
    out = pd.DataFrame({"daily_spread": daily, "z": z, "pos": eff_pos,
                        "pnl": pnl})
    return out.dropna(subset=["pnl"])


def summary_stats(bt: pd.DataFrame) -> dict:
    traded = bt[bt.pos != 0]
    mu, sd, n = bt.pnl.mean(), bt.pnl.std(), len(bt)
    eq = bt.pnl.cumsum()
    return {
        "days": int(n),
        "days_in_position": int(len(traded)),
        "total_pnl_eur_mwh": round(float(bt.pnl.sum()), 1),
        "avg_pnl_per_traded_day": round(float(traded.pnl.mean()), 2) if len(traded) else 0.0,
        "t_stat": round(float(mu / (sd / np.sqrt(n))), 2) if sd > 0 else None,
        "ann_sharpe": round(float(mu / sd * np.sqrt(252)), 2) if sd > 0 else None,
        "max_drawdown": round(float((eq - eq.cummax()).min()), 1),
        "long_side_pnl": round(float(bt.loc[bt.pos > 0, "pnl"].sum()), 1),
        "short_side_pnl": round(float(bt.loc[bt.pos < 0, "pnl"].sum()), 1),
    }


def yearly_stats(bt: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in bt.groupby(bt.index.year):
        sd = g.pnl.std()
        rows.append({
            "year": int(year),
            "pnl": round(float(g.pnl.sum()), 1),
            "trade_days": int((g.pos != 0).sum()),
            "sharpe": round(float(g.pnl.mean() / sd * np.sqrt(252)), 2)
            if sd > 0 else None,
        })
    return pd.DataFrame(rows).set_index("year")


def bootstrap_sharpe(pnl: pd.Series, draws: int = BOOT_DRAWS,
                     mean_block: int = BOOT_BLOCK,
                     seed: int = 7) -> dict:
    """Stationary block bootstrap (Politis-Romano) CI for the annualised
    Sharpe and a p-value for mean P&L <= 0."""
    x = pnl.to_numpy()
    n = len(x)
    rng = np.random.default_rng(seed)
    p_geo = 1.0 / mean_block
    sharpes = np.empty(draws)
    means = np.empty(draws)
    for d in range(draws):
        idx = np.empty(n, dtype=int)
        i = rng.integers(n)
        for t in range(n):
            if t > 0 and rng.random() > p_geo:
                i = (i + 1) % n
            else:
                i = rng.integers(n)
            idx[t] = i
        s = x[idx]
        sd = s.std()
        sharpes[d] = s.mean() / sd * np.sqrt(252) if sd > 0 else 0.0
        means[d] = s.mean()
    return {
        "sharpe_p05": round(float(np.percentile(sharpes, 5)), 2),
        "sharpe_p50": round(float(np.percentile(sharpes, 50)), 2),
        "sharpe_p95": round(float(np.percentile(sharpes, 95)), 2),
        "p_value_mean_le_0": round(float((means <= 0).mean()), 4),
        "draws": draws,
        "mean_block_days": mean_block,
    }


if __name__ == "__main__":
    from power_api import cached_history

    cz, de = cached_history("CZ"), cached_history("DE-LU")
    df = build_spread(cz, de)
    out = Path(__file__).parent.parent / "results"
    out.mkdir(exist_ok=True)

    print("=== CZ-DE day-ahead spread, descriptive ===")
    print(descriptive(df).to_string())

    paper = backtest(df, rt_cost=1.0, tradable=False)
    real = backtest(df, rt_cost=RT_COST_BASE, tradable=True)
    paper.to_csv(out / "cross_border_bt.csv")
    real.to_csv(out / "cross_border_bt_realistic.csv")
    df["spread"].resample("1D").mean().to_csv(out / "cz_de_daily_spread.csv")

    print("\n=== PAPER variant (untradable upper bound, 1 EUR RT) ===")
    paper_stats = summary_stats(paper)
    for k, v in paper_stats.items():
        print(f"  {k:<24} {v}")

    print(f"\n=== TRADABLE variant (+1 day lag, {RT_COST_BASE} EUR RT) ===")
    real_stats = summary_stats(real)
    for k, v in real_stats.items():
        print(f"  {k:<24} {v}")

    print("\n--- tradable variant by year ---")
    ys = yearly_stats(real)
    print(ys.to_string())

    print("\n--- cost sensitivity (annualised Sharpe) ---")
    grid = {}
    for c in RT_COST_GRID:
        s_p = summary_stats(backtest(df, c, tradable=False))["ann_sharpe"]
        s_r = summary_stats(backtest(df, c, tradable=True))["ann_sharpe"]
        grid[c] = {"paper": s_p, "tradable": s_r}
        print(f"  RT {c:>4.1f} EUR/MWh   paper {s_p!s:>6}   tradable {s_r!s:>6}")

    print("\n--- block bootstrap, tradable variant ---")
    boot = bootstrap_sharpe(real.pnl)
    for k, v in boot.items():
        print(f"  {k:<24} {v}")

    summary = {
        "paper": paper_stats,
        "tradable": real_stats,
        "yearly_tradable": ys.reset_index().to_dict("records"),
        "cost_grid_rt_eur_mwh": grid,
        "bootstrap_tradable": boot,
        "params": {"z_entry": Z_ENTRY, "lookback_days": LOOKBACK_D,
                   "rt_cost_base": RT_COST_BASE},
    }
    (out / "cross_border_summary.json").write_text(json.dumps(summary, indent=2))
    print("\nsaved results/cross_border_summary.json")
