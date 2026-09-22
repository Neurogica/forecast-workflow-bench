"""Presentation for the fixed Language Model track; scores remain unmodified."""

import base64
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / "results.json").read_text())
GROUPS = {0: "Larger local", 1: "SLM", 2: "LLM"}
FILTERS = {"All models": None, "SLMs": 1, "Larger local": 0, "LLMs": 2}
CASE_COUNT = DATA.get("case_count", 377)
TRACK = DATA.get("version", "primary-377-v1")
RANK_METRIC = DATA.get("ranking_metric", "loss")
if RANK_METRIC not in ("loss", "g_cost", "score"):
    raise ValueError("Unknown ranking metric")
if not DATA["complete"] or any(
    not r["complete"] or r["scored"] != CASE_COUNT for r in DATA["models"]
):
    raise ValueError("Only complete common-cohort results can be ranked")
RANK = {
    r["model"]: i + 1 for i, r in enumerate(sorted(DATA["models"], key=lambda r: r[RANK_METRIC]))
}
SORT_OPTIONS = (["Combined S · lowest first"] if RANK_METRIC in ("g_cost", "score") else []) + [
    "Loss · lowest first",
    "Credits · lowest first",
    "Validity · highest first",
]
STATUS_PATH = ROOT / "release-status.json"
RELEASE_STATUS = json.loads(STATUS_PATH.read_text()) if STATUS_PATH.exists() else {}
CODE = "https://github.com/Neurogica/forecast-workflow-bench"
DATASET = "https://huggingface.co/datasets/Neurogica/forecast-workflow-bench"


def escape(value):
    return html.escape(str(value), quote=True)


def asset(name, mime):
    return f"data:{mime};base64," + base64.b64encode((ROOT / "assets" / name).read_bytes()).decode()


def header():
    logo = asset("neurogica-logo.webp", "image/webp")
    return f'''<header class="brand-nav">
      <a class="brand" href="https://neurogica.com/" target="_blank" rel="noopener noreferrer"
         aria-label="Neurogica home"><img src="{logo}" alt="NEUROGICA"></a>
      <span class="nav-divider"></span><span class="nav-label">RESEARCH / FWBENCH</span>
      <nav aria-label="Resources">
      <a href="{CODE}" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
      <a href="{DATASET}" target="_blank" rel="noopener noreferrer">Dataset ↗</a></nav>
    </header>'''


def hero():
    pending = ""
    if RELEASE_STATUS.get("status") == "evaluation_in_progress":
        pending = (
            '<p class="release-note"><strong>Expanded release: 1,251 cases.</strong> '
            "Electricity across three cohorts and cycle hire. "
            "Full model evaluation is in progress. "
            "The table below remains the archived 377-case result; "
            "these ranks do not apply to the expanded dataset.</p>"
        )
    scope = (
        "1,251 electricity and cycle-hire cases"
        if CASE_COUNT == 1251
        else "377 electricity-demand cases"
    )
    ranking = (
        "Ranked by the stated loss–cost objective S"
        if RANK_METRIC in ("g_cost", "score")
        else "Ranked by operational loss"
    )
    return f"""<div class="masthead"><section class="leaderboard-intro">
      <h1>FWBench Leaderboard</h1>
      <p>Language Model track · Forecast Workflow Bench</p>
    </section>
    <p class="section-description">Language models use fixed forecasting tools to make
    operational decisions. All models are evaluated on the same {scope}.
    {ranking}; forecast credits measure tool expenditure, not API cost.</p>
    {pending}
    <p class="group-definition">SLMs: local models with fewer than 10 billion total parameters.
    Larger local: 10 billion or more total parameters (including inactive MoE parameters).
    LLMs: hosted models; parameter counts may be undisclosed.</p></div>"""


def leaderboard(group="All models", order=None):
    order = order or SORT_OPTIONS[0]
    target = FILTERS[group]
    items = [r for r in DATA["models"] if target is None or r["group"] == target]
    key = {
        "Combined S · lowest first": lambda r: (r[RANK_METRIC], r["label"]),
        "Loss · lowest first": lambda r: (r["loss"], r["label"]),
        "Credits · lowest first": lambda r: (r["credits"], r["loss"]),
        "Validity · highest first": lambda r: (-r["valid"], r["loss"]),
    }[order]
    body = []
    for r in sorted(items, key=key):
        rank = RANK[r["model"]]
        validity = r["valid"] / r["scored"] * 100
        css = ' class="best-row"' if rank == 1 else ""
        gap_cell = (
            f'<td class="numeric">{r[RANK_METRIC]:.6f}</td>'
            if RANK_METRIC in ("g_cost", "score")
            else ""
        )
        best_label = "LOWEST S" if RANK_METRIC in ("g_cost", "score") else "LOWEST LOSS"
        body.append(f"""<tr{css}><td class="rank">{rank}</td>
          <th scope="row"><span class="model-name">{escape(r["label"])}</span>
          {'<span class="best-label">' + best_label + "</span>" if rank == 1 else ""}</th>
          <td><span class="group-tag group-{r["group"]}">{GROUPS[r["group"]]}</span></td>
          <td class="numeric valid-cell"><span>{r["valid"]}<small> / {r["scored"]}</small></span>
          <span class="valid-track" aria-hidden="true">
          <i style="width:{validity:.4f}%">
          </i>
          </span>
          </td>
          <td class="numeric loss">{r["loss"]:.6f}</td>
          <td class="numeric">{r["credits"]:,.1f}</td>{gap_cell}</tr>""")
    return f"""<span class="mobile-scroll">Swipe the table to compare metrics →</span>
    <div class="table-shell" tabindex="0" role="region" aria-label="Scrollable model results">
    <table class="results-table"><caption class="sr-only">Language Model track results.
    Rank is the global protocol rank and remains unchanged when filtering or sorting.</caption>
    <thead>
    <tr>
    <th scope="col">RANK</th>
    <th scope="col">LANGUAGE MODEL</th>
    <th scope="col">GROUP</th>
    <th scope="col" class="numeric">VALID ↑</th><th scope="col" class="numeric">LOSS ↓</th>
    <th scope="col" class="numeric">FORECAST CREDITS ↓</th>
    {'<th scope="col" class="numeric">S ↓</th>' if RANK_METRIC in ("g_cost", "score") else ""}
    </tr></thead>
    <tbody>{"".join(body)}</tbody></table></div>
    <div class="table-footer">
    <span>{len(items)} of {len(DATA["models"])} models · ranks remain global</span>
    <span>Author-reported results / {escape(TRACK)} / format-v1</span></div>"""


def references():
    gap_header = (
        '<th scope="col" class="numeric">S ↓</th>' if RANK_METRIC in ("g_cost", "score") else ""
    )

    def gap_cell(row):
        return (
            f'<td class="numeric">{row[RANK_METRIC]:.6f}</td>'
            if RANK_METRIC in ("g_cost", "score")
            else ""
        )

    rows = "".join(
        f"""<tr><th scope="row">{escape(r["label"])}</th>
        <td class="numeric">{r["valid"]} / {CASE_COUNT}</td>
        <td class="numeric">{r["loss"]:.6f}</td><td class="numeric">{r["credits"]:,.1f}</td>
        {gap_cell(r)}</tr>"""
        for r in sorted(DATA["fixed_references"], key=lambda r: r[RANK_METRIC])
    )
    return f"""<section class="references">
    <div class="reference-heading">
    <h3>Forecasting reference policies</h3>
      <p>Reference policies, outside the language-model ranking.</p></div>
      <div class="table-shell" tabindex="0" role="region" aria-label="Scrollable reference results">
      <table class="reference-table"><thead><tr><th scope="col">POLICY</th>
      <th scope="col" class="numeric">VALID ↑</th><th scope="col" class="numeric">LOSS ↓</th>
      <th scope="col" class="numeric">FORECAST CREDITS ↓</th>
      {gap_header}
      </tr>
      </thead>
      <tbody>{rows}</tbody>
      </table>
      </div>
      </section>"""


def protocol():
    protocol_doc = "objective_protocol.md" if CASE_COUNT == 1251 else "primary_protocol.md"
    aggregation = (
        (
            "Domain-balanced means: electricity and cycle hire each have 50% weight; "
            "each electricity cohort has 1/6. Dates are averaged within series × lead groups. "
            "S = 0.5 × [(loss − perfect-demand floor) / domain scale + credits / budget]. "
            "Agents were instructed to minimize this objective "
            "(omitting the action-independent floor). "
            "The scales were calibrated on pre-evaluation histories; lower S is better."
        )
        if CASE_COUNT == 1251
        else "Loss and credits are macro-averaged over authority × lead groups."
    )
    scope = (
        "Two domains, four cohorts, overlapping observations and simulated contracts."
        if CASE_COUNT == 1251
        else (
            "One electricity domain, four adjacent target days, "
            "overlapping observations and simulated contracts."
        )
    )
    return f'''<section class="protocol"><div class="section-heading"><div>
      <h2>Evaluation protocol</h2></div>
      <a class="text-link" href="{CODE}/blob/main/docs/{protocol_doc}" target="_blank"
         rel="noopener noreferrer">Read the protocol ↗</a></div>
      <div class="protocol-grid">
      <article>
      <h3>Decision quality</h3>
      <p>Realized shortage and surplus
      loss under capacity-grid and ramp constraints. Invalid plans remain in the score.</p>
      </article>
      <article>
      <h3>Forecast expenditure</h3>
      <p>113,726 credits and
      12 tool calls per case. Credits exclude LLM inference; classical plans are unpriced by
      convention.</p>
      </article>
      <article>
      <h3>Common comparison</h3>
      <p>{aggregation} All {len(DATA["models"])} configurations
      cover the same {CASE_COUNT:,} cases.</p>
      </article>
      </div>
      <details class="scope-note"><summary>Scope, provenance & participation</summary>
      <p>{scope} Results are descriptive and author-reported, not independently certified.</p>
      <p>The initial Language Model track fixes the harness, prompts, forecasting pool and scoring.
      This Space displays results; it does not run models or accept automatic submissions.
      See the <a href="{CODE}/blob/main/docs/leaderboard.md" target="_blank" rel="noopener
      noreferrer">participation protocol</a>
      and <a href="{DATASET}" target="_blank" rel="noopener noreferrer">Dataset card</a> for release
      status.</p>
      </details>
      </section><footer class="brand-footer"><strong>NEUROGICA</strong>
      <span>Forecast Workflow Bench · Language Model track</span>
      <a href="https://neurogica.com/" target="_blank" rel="noopener noreferrer">neurogica.com ↗</a>
      </footer>'''


def stylesheet():
    fonts = []
    for name, family, weight in [
        ("space-grotesk", "Space Grotesk", "300 700"),
        ("inter", "Inter", "100 900"),
        ("ibm-plex-mono", "IBM Plex Mono", "700"),
    ]:
        fonts.append(
            f"@font-face{{font-family:'{family}';src:url('{asset(name + '.woff2', 'font/woff2')}') "
            f"format('woff2');font-weight:{weight};font-style:normal;font-display:swap;}}"
        )
    return (
        "\n".join(fonts)
        + ':root{--fw-city-image:url("'
        + asset("city-background.png", "image/png")
        + '");}'
        + (ROOT / "styles.css").read_text()
    )
