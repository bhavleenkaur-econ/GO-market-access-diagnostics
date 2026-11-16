"""Checks that do not need the raw downloads: the score math and the parking crosswalk."""

import pandas as pd

from scorecard.likely import _labels
from scorecard.parking import FACILITY_TO_STATION
from scorecard.score import condition_average


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
