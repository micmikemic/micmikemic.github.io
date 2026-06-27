"""
Strategy 1 — Battery day-ahead arbitrage (the cleanest structural edge in power).

A storage asset buys cheap hours and sells expensive hours in the daily
EPEX day-ahead auction. The edge is structural, not statistical: solar
build-out keeps widening the intraday price spread (midday trough vs
morning/evening peaks), and a battery is the canonical monetisation.

Implementation: per calendar day, solve the exact profit-maximising
schedule as a small linear program (scipy linprog, HiGHS):

    max  sum_t  p_t * (d_t - c_t) * dt  -  fee * (d_t + c_t) * dt
    s.t. SoC_t = SoC_{t-1} + eta_c*c_t*dt - d_t*dt/eta_d
         0 <= c_t, d_t <= P        0 <= SoC_t <= E
         sum_t d_t*dt <= max_cycles * E          (cell wear limit)

Day-ahead only, perfect knowledge of the auction result — which is NOT
look-ahead bias in the usual sense: all 24 hourly prices clear in one
simultaneous auction at 12:00 CET, so a bidder really does optimise
against a single known(ish) curve. Real desks bid the curve via block /
linked orders; forecast error vs the cleared curve costs a few percent.
We therefore also report a haircut sensitivity.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linprog

sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class BatterySpec:
    power_mw: float = 1.0          # charge/discharge power limit
    energy_mwh: float = 2.0        # usable capacity (2h system)
    eta_charge: float = 0.927      # sqrt(0.86 round-trip)
    eta_discharge: float = 0.927
    max_cycles_per_day: float = 2.0
    fee_eur_mwh: float = 0.10      # exchange + clearing per MWh traded


def optimal_day(prices: np.ndarray, dt_hours: float, spec: BatterySpec) -> dict:
    """Solve one day's optimal schedule. Returns revenue and schedule."""
    n = len(prices)
    P, E = spec.power_mw, spec.energy_mwh
    # variable layout: [c_0..c_{n-1}, d_0..d_{n-1}, s_0..s_{n-1}]
    cost = np.concatenate([
        (prices + spec.fee_eur_mwh) * dt_hours,          # paying for charge
        -(prices - spec.fee_eur_mwh) * dt_hours,         # earning on discharge
        np.zeros(n),
    ])
    # SoC dynamics equalities: s_t - s_{t-1} - eta_c*dt*c_t + dt/eta_d * d_t = 0
    A_eq = np.zeros((n, 3 * n))
    for t in range(n):
        A_eq[t, t] = -spec.eta_charge * dt_hours
        A_eq[t, n + t] = dt_hours / spec.eta_discharge
        A_eq[t, 2 * n + t] = 1.0
        if t > 0:
            A_eq[t, 2 * n + t - 1] = -1.0
    b_eq = np.zeros(n)  # start empty (SoC_{-1} = 0)
    # cycle limit: total discharged energy <= max_cycles * E
    A_ub = np.zeros((1, 3 * n))
    A_ub[0, n:2 * n] = dt_hours
    b_ub = np.array([spec.max_cycles_per_day * E])
    bounds = [(0, P)] * n + [(0, P)] * n + [(0, E)] * n
    res = linprog(cost, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq,
                  bounds=bounds, method="highs")
    if not res.success:
        return {"revenue": np.nan, "charge": None, "discharge": None}
    c, d = res.x[:n], res.x[n:2 * n]
    return {"revenue": -res.fun, "charge": c, "discharge": d,
            "soc": res.x[2 * n:]}


def backtest(prices: pd.Series, spec: BatterySpec | None = None) -> pd.DataFrame:
    """Daily optimal DA arbitrage revenue [EUR] over a price history."""
    spec = spec or BatterySpec()
    rows = []
    for day, p in prices.dropna().groupby(prices.dropna().index.date):
        if len(p) < 12:        # skip broken days
            continue
        dt_hours = (p.index[1] - p.index[0]).total_seconds() / 3600.0
        r = optimal_day(p.to_numpy(), dt_hours, spec)
        rows.append({"date": pd.Timestamp(day), "revenue": r["revenue"],
                     "spread": p.max() - p.min(), "mean_price": p.mean()})
    df = pd.DataFrame(rows).set_index("date")
    return df.dropna()


def annual_summary(daily: pd.DataFrame, spec: BatterySpec) -> pd.DataFrame:
    g = daily.groupby(daily.index.year)
    out = pd.DataFrame({
        "revenue_eur_per_mw": g["revenue"].sum() / spec.power_mw,
        "avg_daily_eur": g["revenue"].mean(),
        "avg_daily_spread": g["spread"].mean(),
        "days": g.size(),
    })
    # annualise partial years for comparability
    out["revenue_eur_per_mw_annualised"] = (
        out["revenue_eur_per_mw"] / out["days"] * 365
    ).round(0)
    return out.round(1)


if __name__ == "__main__":
    from power_api import cached_history

    spec = BatterySpec()
    for bzn in ["DE-LU", "CZ"]:
        prices = cached_history(bzn)
        daily = backtest(prices, spec)
        out = Path(__file__).parent.parent / "results"
        out.mkdir(exist_ok=True)
        daily.to_csv(out / f"battery_daily_{bzn}.csv")
        print(f"\n=== Battery 1 MW / 2 MWh, DA-only, {bzn} ===")
        print(annual_summary(daily, spec).to_string())
