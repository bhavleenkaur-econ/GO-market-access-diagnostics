"""Load GTFS feeds into DuckDB and compute rail service, feeder supply, transfer waits and fares.

The SQL lives in the sql/ folder so it can be read on its own. Python only loads files,
fills in table and date placeholders, and does the one spatial step (stops near stations).
"""

import duckdb
import geopandas as gpd
import pandas as pd

from . import config as C

TABLES = ["stops", "routes", "trips", "stop_times", "calendar", "calendar_dates", "fare_attributes", "fare_rules"]
EMPTY_SCHEMAS = {
    "calendar": "service_id VARCHAR, monday VARCHAR, tuesday VARCHAR, wednesday VARCHAR, thursday VARCHAR, "
    "friday VARCHAR, saturday VARCHAR, sunday VARCHAR, start_date VARCHAR, end_date VARCHAR",
    "calendar_dates": "service_id VARCHAR, date VARCHAR, exception_type VARCHAR",
    "fare_attributes": "fare_id VARCHAR, price VARCHAR",
    "fare_rules": "fare_id VARCHAR, origin_id VARCHAR, destination_id VARCHAR",
}
STOP_TIME_COLS = ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence", "pickup_type", "drop_off_type"]


def sql(name, **params):
    text = (C.SQL / f"{name}.sql").read_text()
    return text.format(**params) if params else text


def connect():
    return duckdb.connect()


def load_feed(con, name):
    """Create schema <name> with one VARCHAR table per GTFS file."""
    folder = C.GTFS_DIR / name
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {name}")
    for table in TABLES:
        path = folder / f"{table}.txt"
        if path.exists() and path.stat().st_size > 0:
            src = f"read_csv('{path}', all_varchar=true, header=true, normalize_names=false)"
            if table == "stop_times":
                cols = con.execute(f"SELECT * FROM {src} LIMIT 0").description
                have = {c[0].strip().lstrip("\ufeff") for c in cols}
                select = ", ".join(
                    f'"{c}"' if c in have else f"NULL::VARCHAR AS {c}" for c in STOP_TIME_COLS
                )
                con.execute(f"CREATE OR REPLACE TABLE {name}.{table} AS SELECT {select} FROM {src}")
            else:
                con.execute(f"CREATE OR REPLACE TABLE {name}.{table} AS SELECT * FROM {src}")
            _strip_bom(con, name, table)
        elif table in EMPTY_SCHEMAS:
            con.execute(f"CREATE OR REPLACE TABLE {name}.{table} ({EMPTY_SCHEMAS[table]})")
    con.execute(sql("active_service_dates", s=name))


def _strip_bom(con, schema, table):
    cols = con.execute(f"SELECT * FROM {schema}.{table} LIMIT 0").description
    for (col, *_rest) in cols:
        clean = col.replace("\ufeff", "").strip()
        if clean != col:
            con.execute(f'ALTER TABLE {schema}.{table} RENAME COLUMN "{col}" TO {clean}')


def representative_weekday(con, name):
    row = con.execute(sql("representative_weekday", s=name, target=_iso(C.GO_WEEKDAY))).fetchone()
    return (row[0], row[1]) if row else (None, 0)


def _iso(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:]}"


def _clock(sec):
    if sec is None or sec != sec:
        return None
    sec = int(sec)
    next_day = ""
    if sec >= 24 * 3600:
        sec -= 24 * 3600
        next_day = " next day"
    return f"{sec // 3600:02d}:{(sec % 3600) // 60:02d}{next_day}"


def apply_service_quality(service):
    """Fill headways when a band has fewer than two trains, and turn the span into clock times.

    One departure has no gap. I use the length of the band, so a single peak train ranks as
    infrequent rather than as a missing value.
    """
    out = service.copy()
    am_window = (C.AM_PEAK[1] - C.AM_PEAK[0]) / 60
    md_window = (C.MIDDAY[1] - C.MIDDAY[0]) / 60
    for value, count, window in (
        ("am_headway_min", "am_gap_n", am_window),
        ("am_max_gap_min", "am_gap_n", am_window),
        ("midday_headway_min", "midday_gap_n", md_window),
        ("midday_max_gap_min", "midday_gap_n", md_window),
    ):
        if value not in out.columns:
            out[value] = pd.NA
        if count not in out.columns:
            out[count] = 0
        thin = out[count].fillna(0).lt(1) | out[value].isna()
        out.loc[thin, value] = window
    out["span_hours"] = (out.last_departure_sec - out.first_departure_sec) / 3600
    out["span_hours"] = out["span_hours"].fillna(0)
    for col in ("saturday_span_hours", "sunday_span_hours"):
        if col not in out.columns:
            out[col] = 0
        out[col] = out[col].fillna(0)
    out["weekend_span_hours"] = (out["saturday_span_hours"] + out["sunday_span_hours"]) / 2
    out["first_departure_clock"] = out["first_departure_sec"].map(_clock)
    out["last_departure_clock"] = out["last_departure_sec"].map(_clock)
    out["offpeak_weekend_departures"] = (
        out.midday_departures + out.evening_departures + out.saturday_departures + out.sunday_departures
    )
    return out


def build_rail(con):
    """Load GO and UP, build rail_events, return per-station service metrics and station points."""
    load_feed(con, "go")
    load_feed(con, "up")
    con.execute(
        sql("rail_events", weekday=_iso(C.GO_WEEKDAY), saturday=_iso(C.GO_SATURDAY), sunday=_iso(C.GO_SUNDAY))
    )
    service = con.execute(
        sql(
            "station_service",
            am0=C.AM_PEAK[0], am1=C.AM_PEAK[1], md0=C.MIDDAY[0], md1=C.MIDDAY[1], ev0=C.EVENING[0],
        )
    ).fetchdf()
    quality = con.execute(
        sql(
            "service_quality",
            am0=C.AM_PEAK[0], am1=C.AM_PEAK[1], md0=C.MIDDAY[0], md1=C.MIDDAY[1],
        )
    ).fetchdf()
    service = service.merge(quality, on="station_id", how="left")
    return apply_service_quality(service)


def rail_stations(con):
    """GO and UP rail stations with coordinates (UP-only Pearson added from the UP feed)."""
    stations = con.execute(
        """
        SELECT DISTINCT e.station_id, s.stop_name, s.stop_lat::DOUBLE AS lat, s.stop_lon::DOUBLE AS lon, s.zone_id
        FROM rail_events e JOIN go.stops s ON s.stop_id = e.station_id
        UNION ALL
        SELECT DISTINCT e.station_id, s.stop_name, s.stop_lat::DOUBLE, s.stop_lon::DOUBLE, NULL
        FROM rail_events e JOIN up.stops s ON s.stop_id = e.station_id
        WHERE e.station_id NOT IN (SELECT stop_id FROM go.stops)
        """
    ).fetchdf()
    stations["station_name"] = (
        stations.stop_name.str.replace(r"^UP Express ", "", regex=True)
        .str.replace(r" GO/UP$| GO Centre$| GO$", "", regex=True)
        .str.replace("Pearson Airport", "Pearson Airport (UP)")
    )
    return gpd.GeoDataFrame(
        stations.drop(columns="stop_name"),
        geometry=gpd.points_from_xy(stations.lon, stations.lat),
        crs=C.CRS_WGS84,
    )


def fares(con):
    return con.execute(sql("fare_to_union")).fetchdf()


def build_feeders(con, stations):
    """Load each local feed, find stops near GO stations, and build local_events."""
    con.execute(
        """CREATE OR REPLACE TABLE local_events (agency VARCHAR, station_id VARCHAR, stop_id VARCHAR,
           route_id VARCHAR, trip_id VARCHAR, arr_sec INT, dep_sec INT, can_alight BOOLEAN, can_board BOOLEAN)"""
    )
    st_m = stations.to_crs(C.CRS_METRIC)
    feed_dates = []
    links = []
    for agency in C.LOCAL_AGENCIES:
        load_feed(con, agency)
        date, trips = representative_weekday(con, agency)
        feed_dates.append({"agency": agency, "representative_weekday": date, "trips_that_day": trips})
        cols = {c[0] for c in con.execute(f"SELECT * FROM {agency}.stops LIMIT 0").description}
        stop_filter = "AND coalesce(location_type, '0') IN ('0', '')" if "location_type" in cols else ""
        stops = con.execute(
            f"""SELECT stop_id, stop_lat::DOUBLE AS lat, stop_lon::DOUBLE AS lon FROM {agency}.stops
                WHERE stop_lat IS NOT NULL AND stop_lat <> '' {stop_filter}"""
        ).fetchdf()
        g = gpd.GeoDataFrame(stops, geometry=gpd.points_from_xy(stops.lon, stops.lat), crs=C.CRS_WGS84)
        g = g.to_crs(C.CRS_METRIC)
        near = gpd.sjoin_nearest(
            g, st_m[["station_id", "geometry"]], how="inner", max_distance=C.FEEDER_RADIUS_M, distance_col="dist_m"
        )
        near["agency"] = agency
        links.append(near[["agency", "stop_id", "station_id", "dist_m"]])
    feeder_stops = pd.concat(links, ignore_index=True)
    con.register("feeder_stops_df", feeder_stops)
    con.execute("CREATE OR REPLACE TABLE feeder_stops AS SELECT * FROM feeder_stops_df")
    for row in feed_dates:
        if row["representative_weekday"] is None:
            continue
        con.execute(
            sql("local_events", agency=row["agency"], s=row["agency"], date=row["representative_weekday"])
        )
    return pd.DataFrame(feed_dates), feeder_stops


def feeder_supply(con):
    return con.execute(sql("feeder_supply", am0=C.AM_PEAK[0], am1=C.AM_PEAK[1])).fetchdf()


def transfer_waits(con, cap_minutes=60):
    con.execute(sql("transfer_waits", min_transfer=C.MIN_TRANSFER_S, cap=cap_minutes * 60))
    return con.execute("SELECT * FROM transfer_waits").fetchdf()


def time_band(sec):
    if C.AM_PEAK[0] <= sec <= C.AM_PEAK[1]:
        return "AM peak"
    if C.MIDDAY[0] <= sec <= C.MIDDAY[1]:
        return "Midday"
    if C.PM_PEAK[0] <= sec <= C.PM_PEAK[1]:
        return "PM peak"
    if sec >= C.EVENING[0]:
        return "Evening"
    return "Other"
