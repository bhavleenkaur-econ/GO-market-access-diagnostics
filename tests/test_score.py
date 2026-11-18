"""Checks that do not need the raw downloads: the score math and the parking crosswalk."""

import duckdb
import pandas as pd

from scorecard import config as C
from scorecard.features import trip_cost
from scorecard.gtfs import apply_service_quality, sql
from scorecard.likely import _labels, confidence_label
from scorecard.parking import FACILITY_TO_STATION
from scorecard.score import condition_average, score


def test_parking_ids_are_unique():
    assert len(FACILITY_TO_STATION) == len(set(FACILITY_TO_STATION.values()))


def test_condition_average_skips_missing_parking():
    frame = pd.DataFrame(
        {
            "service_score": [80.0, 40.0],
            "feeder_score": [80.0, 40.0],
            "walk_score": [80.0, 40.0],
            "parking_score": [20.0, pd.NA],
            "fare_score": [80.0, 40.0],
        }
    )
    weights = {name: 1 for name in ["service", "feeder", "walk", "parking", "fare"]}
    got = condition_average(frame, weights)
    assert abs(got.iloc[0] - 68) < 1e-9
    assert abs(got.iloc[1] - 40) < 1e-9


def test_primary_is_the_largest_deficit_and_a_close_second_is_a_tie():
    deficits = pd.DataFrame({"service": [10.0], "feeder": [40.0], "walk": [32.0], "parking": [5.0], "fare": [-4.0]})
    labels = _labels(deficits)
    assert labels.loc[0, "primary_likely"] == "feeder"
    assert labels.loc[0, "is_tie"]
    assert labels.loc[0, "second_likely"] == "walk"
    assert abs(labels.loc[0, "constraint_share"] - 40 / (10 + 40 + 32 + 5)) < 1e-9


def test_facility_crosswalk_covers_guelph():
    assert FACILITY_TO_STATION["GUEP"] == "GL"


def test_one_departure_in_a_band_uses_the_whole_band_as_the_gap():
    frame = pd.DataFrame(
        {
            "last_departure_sec": [8 * 3600],
            "first_departure_sec": [6 * 3600],
            "midday_departures": [0],
            "evening_departures": [0],
            "saturday_departures": [0],
            "sunday_departures": [0],
            "am_headway_min": [pd.NA],
            "am_max_gap_min": [pd.NA],
            "am_gap_n": [0],
            "midday_headway_min": [30.0],
            "midday_max_gap_min": [40.0],
            "midday_gap_n": [2],
            "saturday_span_hours": [10.0],
            "sunday_span_hours": [pd.NA],
        }
    )
    got = apply_service_quality(frame)
    assert got.loc[0, "am_headway_min"] == 180
    assert got.loc[0, "am_max_gap_min"] == 180
    assert got.loc[0, "midday_max_gap_min"] == 40
    assert got.loc[0, "weekend_span_hours"] == 5
    assert got.loc[0, "first_departure_clock"] == "06:00"
    assert got.loc[0, "span_hours"] == 2


def test_headway_ignores_the_overnight_and_stays_inside_the_band():
    rows = []
    trips = [
        ("T1", 6 * 3600),
        ("T2", 6 * 3600 + 30 * 60),
        ("T3", 7 * 3600),
        ("T4", 10 * 3600),
        ("T5", 12 * 3600),
    ]
    for trip, dep in trips:
        rows.append(_event("S", trip, "S", dep, True))
        rows.append(_event("S", trip, "UN", dep + 3600, False))
    rows.append(_event("S", "SAT1", "S", 8 * 3600, True, day="saturday"))
    rows.append(_event("S", "SAT2", "S", 18 * 3600, True, day="saturday"))
    con = duckdb.connect()
    con.register("rail_src", pd.DataFrame(rows))
    con.execute("CREATE TABLE rail_events AS SELECT * FROM rail_src")
    got = con.execute(
        sql("service_quality", am0=C.AM_PEAK[0], am1=C.AM_PEAK[1], md0=C.MIDDAY[0], md1=C.MIDDAY[1])
    ).fetchdf()
    row = got[got.station_id.eq("S")].iloc[0]
    assert row.am_headway_min == 30
    assert row.am_max_gap_min == 30
    assert row.am_gap_n == 2
    assert row.midday_headway_min == 120
    assert row.midday_gap_n == 1
    assert abs(row.saturday_span_hours - 10) < 1e-9
    assert pd.isna(row.sunday_span_hours)
    assert row.ivt_to_union_min == 60


def test_generalized_cost_adds_fare_to_valued_time():
    # Income $104,000 over 2,080 hours is $50 an hour. Half of that is $25 an hour, or $25/60 a minute.
    # 60 minutes on the train plus half of a 30 minute headway is 75 minutes. Time cost is $31.25.
    # Fare $16.15. Generalized cost $47.40. Per $10,000 of income that is 47.40 / 10.4.
    cost, burden = trip_cost([16.15], [104000], [60], [30], wage_share=0.5, delay_share=0.5)
    assert abs(cost.iloc[0] - 47.40) < 0.01
    assert abs(burden.iloc[0] - 47.40 / 10.4) < 0.01


def test_a_station_beside_the_median_is_near_the_cut_and_a_station_far_below_it_is_clear():
    n = 11
    quality = pd.Series(range(1, n + 1))
    frame = pd.DataFrame(
        {
            "station_id": [f"S{q}" for q in quality],
            "line": "L",
            "in_score": True,
            "shed_pop_jobs": 1000 - quality,
            "commute_to_toronto_share": 0.2,
            "shed_new_dwelling_share": 0.1,
            "am_headway_min": 120 - quality,
            "midday_max_gap_min": 200 - quality,
            "span_hours": quality,
            "weekend_span_hours": quality,
            "feeder_am_arrivals": quality,
            "am_transfer_wait_min": 40 - quality,
            "walk_pop_jobs": quality,
            "walk_reach_ratio": quality / 100,
            "has_scored_lot": True,
            "parking_headroom": quality / 20,
            "fare_burden": 20 - quality,
        }
    )
    got = score(frame)
    assert got.conditions_score.is_monotonic_increasing
    worst = got.iloc[0]
    middle = got.iloc[n // 2]
    assert worst.conditions_gap > C.NEAR_CUT_POINTS
    assert abs(middle.conditions_score - got.attrs["conditions_median"]) <= C.NEAR_CUT_POINTS
    assert bool(middle.near_cut)
    assert not bool(worst.near_cut)
    clear = got[got.threshold_class.eq("clear")]
    assert len(clear) > 0
    assert (clear.conditions_score < got.attrs["conditions_p40"]).all()
    assert (clear.conditions_gap > 0).all()


def test_confidence_is_low_when_land_use_replaces_the_deficit_and_high_when_the_label_is_stable():
    assert confidence_label(0.62, False, False, False, True) == "low"
    assert confidence_label(0.30, False, False, False, False) == "low"
    assert confidence_label(0.62, True, False, False, False) == "medium"
    assert confidence_label(0.62, False, True, False, False) == "medium"
    assert confidence_label(0.62, False, False, True, False) == "medium"
    assert confidence_label(0.62, False, False, False, False) == "high"


def _event(station, trip, stop, dep, toward, day="weekday"):
    return {
        "operator": "GO",
        "station_id": stop,
        "trip_id": trip,
        "day_type": day,
        "can_board": True,
        "toward_union": toward and stop != "UN",
        "dep_sec": dep,
        "arr_sec": dep,
    }
