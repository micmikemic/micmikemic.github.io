"""
Build the substation-to-storage feasibility thesis (PDF).

    python reports/make_substation_thesis.py     # from power_trading

Reuses the dossier's reportlab styling. Charts come from
substation_assets.py; numbers from results/substation_results.json
(run analysis/substation_battery.py first).

Output: reports/Substation_to_Storage_Thesis.pdf
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Frame, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)

from make_dossier import (ACCENT, FRAME_W, INK, MARGIN, MUTE, PAGE_H, PAGE_W,
                          PANEL, RULE, P, bullets, code_block, file_without_main,
                          img, metric_table, styles)


def on_page(canvas, doc):
    """Footer with the thesis title (overrides the dossier's footer)."""
    canvas.saveState()
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.8)
    canvas.line(MARGIN, MARGIN - 6, PAGE_W - MARGIN, MARGIN - 6)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTE)
    canvas.drawString(MARGIN, MARGIN - 16,
                      "Substation to Storage — A Feasibility Thesis")
    canvas.drawCentredString(PAGE_W / 2, MARGIN - 16,
                             "Illustrative techno-economic model — not "
                             "investment advice")
    canvas.drawRightString(PAGE_W - MARGIN, MARGIN - 16, f"p. {doc.page}")
    canvas.restoreState()

BASE = Path(__file__).resolve().parent.parent
RES = BASE / "results"
OUT = Path(__file__).resolve().parent / "Substation_to_Storage_Thesis.pdf"
R = json.loads((RES / "substation_results.json").read_text())
CFG = R["config"]
SC = R["scenarios"]


def eurm(x):
    return f"EUR {x/1e6:.1f}m"


def on_cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.rect(0, PAGE_H - 6.4 * cm, PAGE_W, 6.4 * cm, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#2f6f9f"))
    canvas.rect(0, PAGE_H - 6.55 * cm, PAGE_W, 0.15 * cm, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#ffffff"))
    canvas.setFont("Helvetica-Bold", 27)
    canvas.drawString(MARGIN, PAGE_H - 2.5 * cm, "Substation to Storage")
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(MARGIN, PAGE_H - 3.4 * cm,
                      "A feasibility thesis")
    canvas.setFillColor(HexColor("#b9c6d6"))
    canvas.setFont("Helvetica", 11)
    canvas.drawString(MARGIN, PAGE_H - 4.5 * cm,
                      "Repurposing decommissioned Czech transformer stations "
                      "(transformovny /")
    canvas.drawString(MARGIN, PAGE_H - 5.05 * cm,
                      "rozvodny) as grid batteries with rooftop solar — "
                      "instead of demolishing them")
    canvas.drawString(MARGIN, PAGE_H - 5.75 * cm,
                      "Quantitative model on realised Czech market data  ·  "
                      "June 2026")
    canvas.restoreState()


def callout(story, s, title, body, accent=ACCENT, fill="#eef3f8"):
    inner = [Paragraph(f"<b>{title}</b>", s["h2"]),
             Paragraph(body, s["body"])]
    t = Table([[inner]], colWidths=[FRAME_W])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), HexColor(fill)),
        ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


def build():
    s = styles()
    story = []

    # ---- cover + verdict ----
    story.append(Spacer(1, 5.6 * cm))
    base_adv = SC["base"]["reuse_advantage_npv"]
    callout(
        story, s, "Verdict — a conditional yes, for the right sites",
        "Reusing a decommissioned medium- or high-voltage substation's grid "
        "connection for a battery (plus rooftop PV on the surrounding "
        f"buildings) adds about {eurm(SC['arbitrage_only']['reuse_advantage_npv'])}"
        f"–{eurm(SC['ancillary_rich']['reuse_advantage_npv'])} of net present "
        "value over an equivalent greenfield battery in our representative "
        "20 MW / 40 MWh case — almost entirely from avoided grid-connection "
        "capex and roughly two years' earlier operation. Crucially, that "
        "advantage survives even if balancing-service revenue collapses to "
        "zero. But it applies only where the retained connection is at least a "
        "few MW at distribution or transmission voltage; the thousands of "
        "small 0.4/22 kV kiosk trafostanice are far too small. And because the "
        "connection belongs to the grid operator, the realistic developer is "
        "the DSO/TSO or a partner holding a connection agreement — exactly who "
        "is already doing it at Chvaletice, Kladno and Vitkovice.",
        accent=HexColor("#2e7d5b"), fill="#eef5f0")
    story.append(P("Scope &amp; method: a representative-site techno-economic "
                   "model, not site due diligence. Day-ahead arbitrage is "
                   "computed from realised 2019-2026 Czech auction prices (the "
                   "same LP battery backtest used elsewhere in this project); "
                   "balancing revenue, capex and the connection saving are "
                   "parameterised from 2025-26 Czech market data with explicit "
                   "scenarios and sensitivities. All figures are illustrative "
                   "and not investment advice.", s, "meta"))
    story.append(NextPageTemplate("main"))
    story.append(PageBreak())

    # ---- 1 premise ----
    story.append(P("1 &nbsp; The premise and the question", s, "h1"))
    story.append(P("Across Czechia, ageing transformer and switching stations "
                   "(<i>transformovny</i> and <i>rozvodny</i>) are reaching the "
                   "end of their life — a distribution substation is typically "
                   "rebuilt every 30-40 years, and older or redundant ones are "
                   "demolished outright. The question posed here: rather than "
                   "demolish, could such a site host a grid battery — its cables "
                   "and connection are already there — with solar panels on the "
                   "surrounding buildings, and is that worth doing?", s))
    story.append(P("The short answer is that the buried value of these sites is "
                   "almost never the building or the old iron; it is the "
                   "<b>grid connection</b>. Whether reuse beats demolition is "
                   "therefore a question about one number: how many megawatts, "
                   "at what voltage, the connection can still carry.", s))

    # ---- 2 taxonomy ----
    story.append(P("2 &nbsp; What is actually being demolished — and which "
                   "sites matter", s, "h1"))
    story.append(P("'Transformer station' spans four orders of magnitude of "
                   "capacity. The feasibility verdict flips across that range, "
                   "so the taxonomy is the heart of the analysis.", s))
    story.append(metric_table(
        ["Tier", "Typical site", "Voltage / size", "Battery it supports", "Verdict"],
        [["A", "Kiosk / pole trafostanice", "0.4/22 kV, <1 MVA",
          "< 0.5 MW", "No — too small"],
         ["B", "Distribution substation", "22-110 kV, 10-40 MVA",
          "5-20 MW", "Yes — sweet spot"],
         ["C", "Transmission node / ex-thermal switchyard", "110-400 kV, 100s MW",
          "50-300 MW", "Ideal"]],
        s, col_w=[1.0 * cm, 4.3 * cm, 3.3 * cm, 3.0 * cm, 4.4 * cm]))
    story.append(Spacer(1, 6))
    story.append(P("The thousands of small kiosk <i>trafostanice</i> (Tier A) "
                   "being swapped out in network upgrades are the wrong target: "
                   "a battery there would be a fraction of a megawatt, useful at "
                   "most for a local community microgrid. The prize is Tier B "
                   "and C — and at the top of the range sit retired coal and "
                   "industrial sites whose switchyards already carry hundreds of "
                   "megawatts. One caveat: the common Czech pattern is to "
                   "rebuild the substation in place (as at Trebic-Ptacov, "
                   "demolished while its replacement runs alongside), so the "
                   "connection often stays in network use. 'Free connection' is "
                   "real only where genuine spare capacity remains.", s))

    # ---- 3 connection is the prize ----
    story.append(P("3 &nbsp; Why the grid connection is the prize", s, "h1"))
    story.append(P("A grid connection is the longest-lead, scarcest and often "
                   "costliest part of a battery project. In benchmark all-in "
                   "BESS capex of roughly $125/kWh outside China, about $50/kWh "
                   "— some 40% — is installation and connection, not cells. In "
                   "Germany the transmission connection queue is effectively "
                   "full; the UK is reforming connections explicitly to clear "
                   "the battery pipeline; across Europe developers are pivoting "
                   "to 'co-location' precisely to share an existing connection. "
                   "A live connection means skipping a two-to-four-year queue "
                   "and saving on the order of EUR 60-250 per kW of capacity.", s))
    callout(story, s, "The lever, in one line",
            "A retired substation hands a battery developer the two things "
            "money cannot quickly buy: a connection agreement that already "
            "exists, and the years that would otherwise be spent waiting for "
            "one.")

    # ---- 4 czech market ----
    story.append(P("4 &nbsp; The Czech market right now", s, "h1"))
    story.append(P("The timing is favourable on capacity and policy, and "
                   "treacherous on revenue.", s))
    story.append(P("<b>Boom and policy.</b> Czech battery capacity is set to "
                   "rise from about 2.3 GWh today toward 6 GWh by the end of the "
                   "decade. The 2026 Energy Act amendments let batteries trade "
                   "wholesale and provide FCR, aFRR and mFRR, and streamlined "
                   "grid-connection procedures; the Modernisation Fund and RES+ "
                   "co-fund storage. Tellingly, the flagship projects all sit on "
                   "reused industrial or coal connections: the 230 MWh "
                   "Chvaletice battery on a lignite power-station site, the "
                   "90 MWh Kladno project, CEZ's battery in the Vitkovice "
                   "industrial complex, and BESS Lipnice in the Sokolov coal "
                   "region. The thesis is not hypothetical — it is the "
                   "prevailing build pattern.", s))
    story.append(P("<b>The revenue trap.</b> But the easy money is "
                   "disappearing. The whole Czech FCR-plus-aFRR requirement is "
                   "only around 370 MW, and the fleet is flooding it: aFRR+ "
                   "long-term prices fell about 34% in 2025 (to ~16 EUR/MW/h) "
                   "and FCR about 40% (to ~15 EUR/MW/h), with daily aFRR+ down "
                   "to ~7 EUR/MW/h by mid-2026. Commentators call it 'the end of "
                   "the illusion of easy returns.' A top operator still earned "
                   "around EUR 340k/MW in 2025 via fully-automated multi-market "
                   "trading, but that figure is falling and will not survive "
                   "saturation. The durable floor is energy arbitrage — and "
                   "here Czechia is unusually rich: its day-ahead spreads are "
                   "wide and widening, worth about EUR 88k per MW per year on "
                   "day-ahead alone in 2025 in our LP backtest, before intraday.", s))
    story.append(img("sub_ancillary.png", width=9.0 * cm))
    story.append(P("Czech ČEPS balancing-service prices, EUR/MW/h — the "
                   "collapse that pushes battery economics toward arbitrage.", s,
                   "caption"))

    # ---- 5 the model ----
    story.append(PageBreak())
    story.append(P("5 &nbsp; A quantitative feasibility model", s, "h1"))
    story.append(P(f"We model a representative Tier B site: a retired "
                   f"110/22 kV substation with about {CFG['power_mw']:.0f} MW of "
                   f"usable retained connection, fitted with a "
                   f"{CFG['power_mw']:.0f} MW / "
                   f"{CFG['power_mw']*CFG['duration_h']:.0f} MWh (2-hour) "
                   f"battery and {CFG['pv_mwp']:.0f} MWp of rooftop PV on the "
                   f"surrounding buildings. Revenue stacks day-ahead and "
                   f"intraday arbitrage (from realised prices), a decaying "
                   f"balancing-service contract, and solar. We compare reuse "
                   f"against an identical greenfield battery that must pay for a "
                   f"new connection and wait {CFG['greenfield_delay_years']} "
                   f"years to energise.", s))

    half = FRAME_W / 2
    imgs = Table([[img("sub_capex.png", width=half - 6),
                   img("sub_revenue_stack.png", width=half - 6)]],
                 colWidths=[half, half])
    imgs.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                              ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(imgs)
    story.append(P("Left: capex — reuse avoids the grid-connection block "
                   "entirely. Right: the gross revenue stack in the base case, "
                   "with balancing revenue decaying into an arbitrage-and-solar "
                   "floor.", s, "caption"))

    rows = []
    for sc, label in [("ancillary_rich", "Ancillary-rich (2025 frozen)"),
                      ("base", "Base (ancillary decays)"),
                      ("arbitrage_only", "Arbitrage-only (saturated)")]:
        r = SC[sc]["reuse"]
        g = SC[sc]["greenfield"]
        rows.append([label,
                     f"{r['npv']/1e6:.1f} / {g['npv']/1e6:.1f}",
                     f"{r['irr']*100:.0f}% / {g['irr']*100:.0f}%",
                     f"{r['payback_years']}y / {g['payback_years']}y",
                     f"+{SC[sc]['reuse_advantage_npv']/1e6:.1f}"])
    story.append(P("<b>Results — reuse / greenfield, 15-year, 8% discount.</b>",
                   s, "h2"))
    story.append(metric_table(
        ["Scenario", "NPV EURm", "IRR", "Payback", "Reuse edge EURm"],
        rows, s, col_w=[6.0 * cm, 3.1 * cm, 2.6 * cm, 2.6 * cm, 2.7 * cm]))
    story.append(Spacer(1, 6))
    story.append(img("sub_cashflow.png", width=FRAME_W))
    story.append(P("Cumulative cash for the reuse case across scenarios. Even "
                   "arbitrage-only — balancing revenue gone — pays back inside "
                   "the asset life.", s, "caption"))
    story.append(img("sub_sensitivity.png", width=FRAME_W))
    story.append(P("Sensitivity of reuse NPV to the two swing variables: how "
                   "fast balancing prices decay, and battery capex per kWh. The "
                   "project stays NPV-positive across the plausible range; the "
                   "reuse edge over greenfield is more robust still, because it "
                   "is a capex and timing difference, not a revenue bet.", s,
                   "caption"))

    # ---- 6 solar ----
    story.append(P("6 &nbsp; Rooftop solar on the surrounding buildings", s, "h1"))
    story.append(P("Solar is a sensible companion but a junior partner. Roof "
                   "area on a substation's ancillary buildings is limited, so "
                   "a couple of MWp is realistic — perhaps EUR 0.1-0.2m a year "
                   "of generation at a cannibalised midday capture price. Its "
                   "real value is synergy and zero marginal connection cost: the "
                   "PV charges the battery cheaply at the midday solar trough "
                   "(often near or below zero — Czechia saw a sharp rise in "
                   "negative-price hours), which the battery then shifts into "
                   "the evening peak, and both assets share the one connection "
                   "and one set of balance-of-plant. It improves the economics "
                   "at the margin; it does not carry the project.", s))

    # ---- 7 decision rule ----
    story.append(P("7 &nbsp; When it is worth doing — the decision rule", s, "h1"))
    story += bullets([
        "<b>Connection test.</b> Reuse beats demolition when the retained "
        "connection carries at least roughly 5 MW at 22 kV or above and real "
        "spare capacity exists. Below that, the connection is worth less than "
        "the cleared land — demolish.",
        "<b>Owner test.</b> The connection is the DSO's or TSO's asset. The "
        "credible developer is the grid operator, the site owner, or a partner "
        "with a connection agreement — not an outside party assuming the cables "
        "are free for the taking.",
        "<b>Condition test.</b> The value is the line, the bay, the land and "
        "the permits — not the old transformer, which a battery replaces with "
        "its own inverters and transformer anyway. Brownfield liabilities "
        "(contamination, asbestos, foundations) must net out below the "
        "connection saving.",
        "<b>Counter-incentive.</b> Demolition itself can be subsidised (the "
        "Ministry for Regional Development funds brownfield clearance), and the "
        "operator may need the bay for the replacement substation. Reuse must "
        "clear that bar too.",
    ], s)

    # ---- 8 risks ----
    story.append(P("8 &nbsp; Risks", s, "h1"))
    story += bullets([
        "<b>Balancing saturation.</b> Modelled explicitly; the tiny ~370 MW "
        "national requirement saturates quickly and prices are already in "
        "steep decline.",
        "<b>Arbitrage cannibalisation.</b> The same battery build-out that "
        "saturates balancing also narrows the day-ahead spreads arbitrage "
        "relies on — so even the arbitrage-only case is optimistic over a full "
        "15 years; treat it as an upper bound on the floor.",
        "<b>Bankability.</b> Standalone merchant batteries are reported at "
        "5-7% unlevered IRR in tougher European markets; Czech spreads are "
        "better but volatile, and revenue is exposed, not contracted.",
        "<b>Brownfield and technical.</b> Contamination, protection upgrades "
        "and connection re-rating can erode the saving; due diligence per site "
        "is essential.",
    ], s)

    # ---- 9 verdict ----
    story.append(P("9 &nbsp; Verdict", s, "h1"))
    callout(story, s, "Worth doing — selectively, and as the grid owner",
            "For Tier B and C sites, reusing the connection for a battery beats "
            "both greenfield and demolition: the connection is the scarce "
            "asset, and reuse banks its value plus two years of lead time, an "
            f"edge of roughly {eurm(base_adv)} of NPV in the base case that "
            "holds even if balancing revenue disappears. It is not a strategy "
            "for the small kiosk stations, and it is realistically executed by "
            "the grid operator or a connection-holding partner — which is "
            "precisely the pattern now playing out across the Czech coal and "
            "industrial fleet. The headline revenue numbers will fall as the "
            "market saturates; the connection-reuse advantage will not.",
            accent=HexColor("#2e7d5b"), fill="#eef5f0")

    story.append(P("References", s, "h2"))
    story += bullets([
        "CzechTrade / ess-news — Czech large-scale storage; AlphaESS Chvaletice "
        "(230 MWh) and Kladno (90 MWh); CEZ ESCO Vitkovice battery; SUAS BESS "
        "Lipnice.",
        "oEnergetice / Prumyslova ekologie — Czech balancing-service auction "
        "results 2025-26 ('the end of the illusion of easy returns'); ČEPS "
        "FCR/aFRR/mFRR prices.",
        "ess-news (2026) — 'Making the case for brownfield battery builds'; "
        "co-location and connection-reuse economics in Europe.",
        "Ember / SolarPower Europe — European BESS capex and revenue-stacking "
        "benchmarks 2025-26.",
        "solarninovinky / FENIX, Nano Energies, Suena — Czech and German "
        "operator revenue per MW, 2025.",
        "This project — CZ day-ahead LP arbitrage backtest on realised "
        "2019-2026 EPEX prices (Energy-Charts / Fraunhofer ISE).",
    ], s)

    # ---- appendix: model code ----
    story.append(PageBreak())
    story.append(P("Appendix &nbsp; The feasibility model (code)", s, "h1"))
    story.append(P("The full techno-economic model used above. Assumptions are "
                   "named constants with their sources in comments; the three "
                   "scenarios and the sensitivity sweep are the output.", s))
    story += code_block("python &middot; analysis/substation_battery.py",
                        file_without_main(BASE / "analysis" / "substation_battery.py"), s)

    doc = BaseDocTemplate(str(OUT), pagesize=A4, leftMargin=MARGIN,
                          rightMargin=MARGIN, topMargin=MARGIN,
                          bottomMargin=2.0 * cm,
                          title="Substation to Storage — A Feasibility Thesis",
                          author="Quant desk")
    frame = Frame(MARGIN, 2.0 * cm, FRAME_W, PAGE_H - MARGIN - 2.0 * cm, id="f")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=on_cover),
        PageTemplate(id="main", frames=[frame], onPage=on_page),
    ])
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    build()
