"""Build a versioned transport cohort from official TfL archives, without scoring."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from forecast_workflow.core.io import digest, write_json, write_jsonl
from forecast_workflow.core.schema import Catalog, SeriesRecord, Task
from forecast_workflow.decision.contract import GRID
from forecast_workflow.tools.server import TOOLS


def aggregate(source, station_count):
    acquisition = json.loads((source / "acquisition.json").read_text())
    frames = []
    for resource in acquisition["resources"]:
        path = source / resource["file"]
        assert digest(path) == resource["sha256"]
        if path.suffix == ".csv":
            frames.append(
                pd.read_csv(
                    path,
                    dtype=str,
                    usecols=["Number", "Start date", "Start station number", "Start station"],
                )
            )
    frame = pd.concat(frames, ignore_index=True)
    assert not frame.isna().any().any()
    duplicates = frame[frame.duplicated("Number", keep=False)]
    # Midnight boundary records overlap in official consecutive files.
    assert all(len(g.drop_duplicates()) == 1 for _, g in duplicates.groupby("Number"))
    duplicate_count = int(frame.duplicated("Number").sum())
    frame = frame.drop_duplicates("Number")
    # These dates are all in British Summer Time; no ambiguous DST transition.
    frame["timestamp"] = (
        pd.to_datetime(frame["Start date"])
        .dt.tz_localize("Europe/London", ambiguous="raise", nonexistent="raise")
        .dt.tz_convert("UTC")
        .dt.floor("h")
    )
    start = pd.Timestamp("2026-04-01", tz="Europe/London").tz_convert("UTC")
    stop = pd.Timestamp("2026-06-01", tz="Europe/London").tz_convert("UTC")
    frame = frame[(frame.timestamp >= start) & (frame.timestamp < stop)]
    # A complete official reporting interval is necessary before absent trips are zero.
    hours = pd.date_range(start, stop, freq="h", inclusive="left")
    assert set(frame.timestamp) == set(hours), "An entire system hour is missing"
    selection = frame[frame.timestamp < start + pd.Timedelta(days=7)]
    counts = selection.groupby("Start station number").size().rename("count").reset_index()
    stations = counts.sort_values(["count", "Start station number"], ascending=[False, True]).head(
        20
    )
    grouped = frame.groupby(["Start station number", "timestamp"]).size()
    names = frame.drop_duplicates("Start station number").set_index("Start station number")[
        "Start station"
    ]
    output = {}
    for station in stations["Start station number"]:
        output[station] = grouped.loc[station].reindex(hours, fill_value=0).astype(int)
    return (
        output,
        names,
        dict(
            unique_recorded_trips=len(frame),
            exact_boundary_duplicates_removed=duplicate_count,
            global_hours=len(hours),
            selection_counts=stations.to_dict(orient="records"),
        ),
    )


def build(source, output, config, profile):
    source, ROOT, CONFIG, PROFILE = map(Path, (source, output, config, profile))
    ROOT.mkdir(parents=True, exist_ok=False)
    selection = json.loads(CONFIG.read_text())
    selection.update(
        config_sha256=digest(CONFIG),
        builder_sha256=digest(Path(__file__)),
        acquisition_sha256=digest(source / "acquisition.json"),
    )
    write_json(ROOT / "selection.json", selection)
    series, names, source_audit = aggregate(source, selection["stations"])
    acquisition = json.loads((source / "acquisition.json").read_text())
    profile = json.loads(PROFILE.read_text())
    profile.pop("budgets", None)
    tasks, cases, excluded = [], [], []
    for station, values in sorted(series.items()):
        values.rename("value").rename_axis("timestamp").to_csv(ROOT / f"aggregate-{station}.csv")
        for date in selection["target_dates"]:
            start = pd.Timestamp(date, tz="Europe/London").tz_convert("UTC")
            times = pd.date_range(start, periods=24, freq="h")
            actual = values.reindex(times)
            for lead in selection["lead_days"]:
                as_of = start - pd.Timedelta(days=lead)
                last = as_of - pd.Timedelta(hours=3)
                history = values.reindex(pd.date_range(end=last, periods=336, freq="h"))
                family = "day_ahead" if lead == 1 else "week_ahead"
                cid = f"TFL-{station}-{date}-{family}"
                reason = None
                if history.isna().any() or actual.isna().any():
                    reason = "source_coverage"
                elif (
                    history.mean() <= 0
                    or (
                        history.to_frame("value")
                        .groupby(history.index.tz_convert("Europe/London").date)
                        .agg(["sum", "count"])["value"]
                        .query("count == 24")["sum"]
                        == 0
                    ).any()
                ):
                    reason = "inactive_history_day"
                if reason:
                    excluded.append(dict(case_id=cid, reason=reason))
                    continue
                scale = float(history.mean())
                sid, eid = f"tfl_{station}_departures", f"p3--{cid}--b113726"
                ep = ROOT / "episodes" / eid
                path = ep / "series" / f"{sid}.csv"
                path.parent.mkdir(parents=True)
                history.rename("value").rename_axis("timestamp").to_csv(path)
                record = SeriesRecord(
                    series_id=sid,
                    name=f"TfL cycle-hire departures: {names[station]}",
                    path=f"series/{sid}.csv",
                    unit="departures/hour",
                    source="Transport for London",
                    source_url=acquisition["source_page"],
                    license_id=acquisition["license_id"],
                    attribution="; ".join(acquisition["attribution"]),
                    sha256=digest(path),
                    observed_start=history.index[0],
                    observed_end=last,
                    snapshot_at=acquisition["resources"][0]["retrieved_at"],
                    quality=(
                        "Recorded completed departures; zero-count hours retained; "
                        "BST converted to UTC. "
                        "Retrospective archive, not unconstrained latent demand or "
                        "an as-published vintage."
                    ),
                )
                write_json(ep / "catalog.json", Catalog(series=[record]).model_dump(mode="json"))
                write_json(ep / "forecast_budget.json", profile | dict(budget=113726))
                write_json(
                    ep / "probabilistic_forecasts.json",
                    dict(
                        models=["seasonal_empirical", "chronos_bolt_tiny", "chronos2", "timesfm25"]
                    ),
                )
                terms = dict(
                    billing="imbalance",
                    block_hours=3,
                    reservation=0.3,
                    shortage=1.0,
                    emergency=0.0,
                    emergency_buffer=0.1,
                    adjustment=0.0,
                    ramp=0.3,
                    hourly_priority=np.repeat(
                        np.roll([1.0, 1.0, 2.0, 1.5], pd.Timestamp(date).weekday() % 4), 6
                    ).tolist(),
                )
                contract = dict(
                    id=eid,
                    terms=terms,
                    scale=scale,
                    capacity_grid=(GRID * scale).tolist(),
                    unit="departures/hour",
                    domain="cycle_hire",
                    observation_support="nonnegative",
                    target_start=start.isoformat(),
                    target_end=(start + pd.Timedelta(days=1)).isoformat(),
                    as_of=as_of.isoformat(),
                )
                write_json(ep / "business_contract.json", contract)
                instruction = (
                    f"At {as_of.isoformat()}, commit cycle-hire service capacity for {sid} during "
                    f"[{contract['target_start']}, {contract['target_end']}) UTC. "
                    "The target is recorded hourly departures; capacity is a "
                    "simulated service rate in departures/hour, "
                    "not bike inventory. Return JSON decisions b00 through b07 "
                    "for eight consecutive three-hour blocks. "
                    "Values must belong to capacity_grid. Adjacent capacities "
                    "divided by scale may differ by at most ramp. "
                    "Minimize mean hourly "
                    "surplus_price*max(a-y,0)+hourly_priority[h]*max(y-a,0), "
                    "with a,y normalized by scale. "
                    "No total-capacity constraint, change fee or emergency "
                    "charge. Forecast budget: 113726 credits. "
                    "Choose whether to buy forecasts, their model, horizon and "
                    "context. Timestamps label measured hour starts. "
                    "All eight classical reference methods are available through "
                    "classical_plan. The available forecast pool "
                    "is shown in catalog. Shared decision support is available: "
                    "capacity_plan.submission can be submitted. "
                    "Conditional expected loss is not measured validation. No "
                    "future observations are visible. "
                    "Missing, duplicate, nonfinite, off-grid and ramp-violating "
                    "actions are invalid. "
                    "Real completed-trip counts with simulated costs; unmet "
                    "rental demand and inventory dynamics are not observed. "
                    "Parameters: "
                    + json.dumps(
                        dict(
                            surplus_price=0.3,
                            ramp=0.3,
                            scale=scale,
                            capacity_grid=contract["capacity_grid"],
                            hourly_priority=terms["hourly_priority"],
                        )
                    )
                )
                task = Task(
                    task_id=eid,
                    group_id=station,
                    split="test",
                    family="decision_flexible_" + family,
                    instruction=instruction,
                    as_of=as_of,
                    max_calls=12,
                    max_output_tokens=16384,
                    allowed_tools=TOOLS,
                )
                payload = task.model_dump(mode="json")
                write_json(ep / "task.json", payload)
                tasks.append(payload)
                write_json(
                    ROOT / "private" / f"{cid}.json",
                    dict(
                        case_id=cid,
                        actual=actual.tolist(),
                        timestamps=[t.isoformat() for t in times],
                    ),
                )
                cases.append(
                    dict(
                        case_id=cid,
                        authority=station,
                        group_id=station,
                        domain="cycle_hire",
                        family=family,
                        target_start=start.isoformat(),
                        target_end=contract["target_end"],
                        as_of=as_of.isoformat(),
                        last_visible=last.isoformat(),
                        expected_horizon=50 if lead == 1 else 194,
                    )
                )
    write_jsonl(ROOT / "tasks.jsonl", tasks)
    write_json(
        ROOT / "manifest.json",
        dict(
            cases=cases,
            excluded=excluded,
            candidate_cases=selection["stations"]
            * len(selection["target_dates"])
            * len(selection["lead_days"]),
            source_cases=len(cases),
            distinct_station_target_days=len({(c["authority"], c["target_start"]) for c in cases}),
            selection_sha256=digest(ROOT / "selection.json"),
            tasks_sha256=digest(ROOT / "tasks.jsonl"),
            source_audit=source_audit,
            license_id=acquisition["license_id"],
        ),
    )
    print(json.dumps(dict(cases=len(cases), excluded=excluded, source_audit=source_audit)))
