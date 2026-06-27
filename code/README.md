# Code

The Python behind the research on the main page. Backtests run on realised
EPEX day-ahead auction prices (2019–2026), sourced via ENTSO-E and
Energy-Charts (Fraunhofer ISE, CC BY 4.0).

| File | Strategy / model |
|------|------------------|
| `battery_arbitrage.py` | Battery day-ahead arbitrage - per-day optimal dispatch as a linear program (scipy / HiGHS), with SoC dynamics, round-trip efficiency and a cycle-life cap. |
| `solar_spread.py` | Solar cannibalisation spread - short the midday block, long the evening block; unconditional, seasonal and year-by-year, plus negative-price-hour tracking as a decay monitor. |
| `cross_border.py` | CZ–DE cross-border spread - descriptive stats plus a mean-reversion backtest with an explicit paper-vs-tradable timing split and a stationary block bootstrap for the Sharpe CI. |
| `substation_model.py` | Substation-to-storage feasibility - techno-economic model (NPV / IRR / payback) with three revenue scenarios and a sensitivity sweep. |

## Note on data

The strategy scripts import `cached_history` from a small `power_api`
module (the ENTSO-E / Energy-Charts fetch-and-cache layer), which isn't
included here. The logic that matters - the optimisation, the spread
construction, the statistics - is all in the files above and runs against
any hourly price series indexed by timestamp.

Built with: Python · numpy · pandas · scipy (HiGHS).
