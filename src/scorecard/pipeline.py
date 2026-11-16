"""Run the scorecard from the raw files and write the tables the notebooks and the brief use."""

import json

import pandas as pd

from . import brief, config as C, features, gtfs, likely, parking, recommendations, score, viz


def run(save=True):
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    con = gtfs.connect()
    service = gtfs.build_rail(con)
    stations = gtfs.rail_stations(con)
    fares = gtfs.fares(con)
    feed_dates, _links = gtfs.build_feeders(con, stations)
    feeders = gtfs.feeder_supply(con)
    waits = gtfs.transfer_waits(con)
    park = parking.load()
    table, walks, sheds = features.build(stations, service, fares, feeders, waits, park)
    table = score.score(table)
    table = likely.diagnose(table)
    recs = recommendations.build(table)

    meta = {
        "market_median": table.attrs.get("market_median"),
        "conditions_median": table.attrs.get("conditions_median"),
        "priority_by_scheme": table.attrs.get("priority_by_scheme"),
        "priority_stable": table.attrs.get("priority_stable"),
        "weight_spearman": table.attrs.get("weight_spearman"),
        "reference_median": table.attrs.get("reference_median"),
        "reference_n": table.attrs.get("reference_n"),
        "weekday": C.GO_WEEKDAY,
        "saturday": C.GO_SATURDAY,
        "sunday": C.GO_SUNDAY,
    }
    if save:
        table.drop(columns=[], errors="ignore").to_csv(C.PROCESSED / "station_scorecard.csv", index=False)
        recs.to_csv(C.PROCESSED / "recommendations.csv", index=False)
        feed_dates.to_csv(C.PROCESSED / "feeder_service_dates.csv", index=False)
        waits.to_parquet(C.PROCESSED / "transfer_waits.parquet", index=False)
        walks.to_crs(C.CRS_WGS84).to_parquet(C.PROCESSED / "walksheds.parquet")
        sheds.to_crs(C.CRS_WGS84).to_parquet(C.PROCESSED / "station_sheds.parquet")
        (C.PROCESSED / "run_meta.json").write_text(json.dumps(meta, indent=2, default=float))
        viz.all_figures(table, walks)
        brief.write(table, recs, meta)
    table.attrs.update(meta)
    return table, recs, waits, feed_dates


def load():
    table = pd.read_csv(C.PROCESSED / "station_scorecard.csv")
    recs = pd.read_csv(C.PROCESSED / "recommendations.csv")
    meta = json.loads((C.PROCESSED / "run_meta.json").read_text())
    table.attrs.update(meta)
    return table, recs, meta
