# Power market research — Michal Junek

Quantitative power-market strategies and storage feasibility work, backtested on realised EPEX day-ahead auction data (2019–2026), built in Python.

**Live page:** https://micmikemic.github.io/  *(replace USERNAME after publishing — see below)*

## Contents

| Work | Type | What it is |
|------|------|-----------|
| [One-page summary](docs/strategy_summary.pdf) | overview | All three strategies on a single page |
| [Battery day-ahead arbitrage](docs/battery_arbitrage.pdf) | structural | LP-optimal (HiGHS) battery dispatch vs the daily auction curve |
| [Solar cannibalisation spread](docs/solar_cannibalisation.pdf) | structural | Sell midday / buy evening block, volume-neutral |
| [CZ–DE cross-border spread](docs/cz_de_spread.pdf) | statistical | Mean-reversion on the coupled day-ahead spread, shown sceptically |
| [Substation to storage](docs/substation_to_storage.pdf) | techno-economic | Feasibility of reusing decommissioned Czech substations as grid batteries |

All figures are on realised auction prices, costs included, per unit of position. Illustrative research, not investment advice. Past performance does not indicate future results.

Data: EPEX SDAC day-ahead auctions via Energy-Charts (Fraunhofer ISE, CC BY 4.0).

## Stack

Python · pandas · scipy / HiGHS · SQL · C

## Contact

junek05michal@gmail.com
