"""Analysis 1. Market potential against enabling conditions, as percentile scores.

A higher score is better. Parking is left blank where there is no commuter lot, and the
condition average is renormalized over the conditions that apply.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from . import config as C
from .features import trip_cost


def _pct(values):
    return values.rank(method="average", pct=True) * 100


def _blend(frame, columns):
    parts = [_pct(frame[c]) for c in columns]
    return pd.concat(parts, axis=1).mean(axis=1)


def condition_average(frame, weights):
    num = pd.Series(0.0, index=frame.index)
    den = pd.Series(0.0, index=frame.index)
    for name, weight in weights.items():
        values = frame[f"{name}_score"]
        use = values.notna()
        num = num + values.fillna(0) * weight * use
        den = den + weight * use
    return num / den


def score(features):
    out = features.copy()
    scored = out["in_score"]
    idx = out.index[scored]

    market = pd.DataFrame(
        {
            "shed_pop_jobs": _pct(out.loc[idx, "shed_pop_jobs"]),
            "commute_to_toronto_share": _pct(out.loc[idx, "commute_to_toronto_share"]),
            "recent_dwelling_share": _pct(out.loc[idx, "shed_new_dwelling_share"]),
        }
    )
    out.loc[idx, "market_score"] = market.mean(axis=1)
    out.loc[idx, "market_pop_jobs_rank"] = market["shed_pop_jobs"]
    out.loc[idx, "market_commute_rank"] = market["commute_to_toronto_share"]
    out.loc[idx, "market_growth_rank"] = market["recent_dwelling_share"]

    # A short headway and a short midday gap are better, so those two ranks are reversed.
    # Span is better when it is longer. Trip counts stay in the table and do not enter the score.
    am_headway = 100 - _pct(out.loc[idx, "am_headway_min"])
    midday_gap = 100 - _pct(out.loc[idx, "midday_max_gap_min"])
    weekday_span = _pct(out.loc[idx, "span_hours"])
    weekend_span = _pct(out.loc[idx, "weekend_span_hours"])
    out.loc[idx, "service_score"] = pd.concat(
        [am_headway, midday_gap, weekday_span, weekend_span], axis=1
    ).mean(axis=1)

    arrivals = _pct(out.loc[idx, "feeder_am_arrivals"])
    wait = out.loc[idx, "am_transfer_wait_min"]
    wait_score = 100 - _pct(wait)
    out.loc[idx, "feeder_score"] = np.where(wait.notna(), (arrivals + wait_score) / 2, arrivals)

    out.loc[idx, "walk_score"] = _blend(out.loc[idx], ["walk_pop_jobs", "walk_reach_ratio"])
    out.loc[idx, "walk_market_rank"] = _pct(out.loc[idx, "walk_pop_jobs"])

    lot = idx[out.loc[idx, "has_scored_lot"].fillna(False)]
    out.loc[lot, "parking_score"] = _pct(out.loc[lot, "parking_headroom"])

    burden = out.loc[idx, "fare_burden"]
    out.loc[idx, "fare_score"] = 100 - _pct(burden)

    for scheme, weights in C.WEIGHT_SCHEMES.items():
        out.loc[idx, f"conditions_{scheme}"] = condition_average(out.loc[idx], weights)
    out.loc[idx, "conditions_score"] = out.loc[idx, f"conditions_{C.PRIMARY_SCHEME}"]

    market_cut = out.loc[idx, "market_score"].median()
    condition_cut = out.loc[idx, "conditions_score"].median()
    out["high_market"] = False
    out["strong_conditions"] = False
    out.loc[idx, "high_market"] = out.loc[idx, "market_score"] >= market_cut
    out.loc[idx, "strong_conditions"] = out.loc[idx, "conditions_score"] >= condition_cut
    out["quadrant"] = np.select(
        [
            ~out["in_score"],
            out["high_market"] & ~out["strong_conditions"],
            out["high_market"] & out["strong_conditions"],
            ~out["high_market"] & out["strong_conditions"],
        ],
        ["not scored", "priority", "market and conditions", "conditions ahead of market"],
        default="market and conditions both thin",
    )
    out.attrs["market_median"] = float(market_cut)
    out.attrs["conditions_median"] = float(condition_cut)
    out.loc[idx, "conditions_gap"] = condition_cut - out.loc[idx, "conditions_score"]
    out.loc[idx, "near_cut"] = (
        (out.loc[idx, "market_score"] - market_cut).abs().le(C.NEAR_CUT_POINTS)
        | (out.loc[idx, "conditions_score"] - condition_cut).abs().le(C.NEAR_CUT_POINTS)
    )
    # A lower percentile is a stricter conditions cut: a station below the 40th is also
    # below the median and below the 60th. Clear means all three. Threshold-sensitive
    # means the median says priority and the 40th does not.
    p40 = float(out.loc[idx, "conditions_score"].quantile(0.40))
    p60 = float(out.loc[idx, "conditions_score"].quantile(0.60))
    high_market = out.loc[idx, "market_score"] >= market_cut
    below40 = out.loc[idx, "conditions_score"] < p40
    below50 = out.loc[idx, "conditions_score"] < condition_cut
    below60 = out.loc[idx, "conditions_score"] < p60
    out.loc[idx, "threshold_class"] = np.select(
        [high_market & below40, high_market & below50, high_market & below60],
        ["clear", "threshold-sensitive", "looser cut only"],
        default="not priority",
    )
    out.attrs["conditions_p40"] = p40
    out.attrs["conditions_p60"] = p60
    out.attrs["priority_clear"] = sorted(out.loc[idx].loc[high_market & below40, "station_id"])
    out.attrs["priority_threshold_sensitive"] = sorted(out.loc[idx].loc[high_market & below50 & ~below40, "station_id"])
    out.attrs["priority_looser_only"] = sorted(out.loc[idx].loc[high_market & below60 & ~below50, "station_id"])

    # Corridor-relative split, so a weak Lakeshore station is not judged only against Richmond Hill.
    line_market = out.loc[idx].groupby("line")["market_score"].transform("median")
    line_conditions = out.loc[idx].groupby("line")["conditions_score"].transform("median")
    out.loc[idx, "priority_in_corridor"] = (out.loc[idx, "market_score"] >= line_market) & (
        out.loc[idx, "conditions_score"] < line_conditions
    )

    sets = []
    for scheme in C.WEIGHT_SCHEMES:
        cut = out.loc[idx, f"conditions_{scheme}"].median()
        sets.append(set(out.loc[idx][(out.loc[idx, "market_score"] >= market_cut) & (out.loc[idx, f"conditions_{scheme}"] < cut)].station_id))
    out.attrs["priority_by_scheme"] = {name: sorted(s) for name, s in zip(C.WEIGHT_SCHEMES, sets)}
    out.attrs["priority_stable"] = sorted(set.intersection(*sets))
    ranks = out.loc[idx, [f"conditions_{s}" for s in C.WEIGHT_SCHEMES]]
    out.attrs["weight_spearman"] = {
        f"{a}_vs_{b}": float(spearmanr(ranks[f"conditions_{a}"], ranks[f"conditions_{b}"]).statistic)
        for a, b in (("equal", "access_heavy"), ("equal", "service_heavy"), ("access_heavy", "service_heavy"))
    }
    return out


def _fare_argmax(table, burden):
    """Name of the largest deficit if the fare burden is replaced and the other deficits stay."""
    idx = table.index[table["in_score"].fillna(False)]
    score = pd.Series(np.nan, index=table.index)
    score.loc[idx] = 100 - _pct(burden.loc[idx])
    reference = table["in_score"].fillna(False) & table["quadrant"].eq("market and conditions")
    ref_median = score.loc[reference].median()
    changed = []
    focus = table["quadrant"].eq("priority") | table["station_id"].isin(C.KITCHENER_CASE)
    for i in table.index[focus]:
        best_name, best_value = None, -np.inf
        for name in C.CONDITIONS:
            if name == "fare":
                value = ref_median - score.loc[i]
            else:
                value = table.loc[i, f"deficit_{name}"]
            if pd.isna(value):
                continue
            if value > best_value:
                best_name, best_value = name, value
        current = table.loc[i, "numeric_primary"]
        if best_name != current and not (pd.isna(best_name) and pd.isna(current)):
            changed.append(table.loc[i, "station_name"])
    return changed


def fare_sensitivity(table):
    """Whether the fare label survives a different price or a different value of time.

    The GTFS file has one price per zone pair, so a PRESTO discount is not in the feed.
    A percent reduction scales every fare and, once time is in the cost, can still change
    a rank. A flat reduction changes ranks even before time is added, because incomes differ.
    """
    single = True
    if "fare_product_n" in table.columns and table["fare_product_n"].dropna().gt(1).any():
        single = False
    scenarios = {
        "flat_discount": dict(fare=table.fare_to_union - C.FARE_FLAT_DISCOUNT, wage=C.VOT_WAGE_SHARE, delay=C.FREQUENCY_DELAY_SHARE),
        "percent_discount": dict(fare=table.fare_to_union * (1 - C.FARE_PERCENT_DISCOUNT), wage=C.VOT_WAGE_SHARE, delay=C.FREQUENCY_DELAY_SHARE),
        "timed_arrival": dict(fare=table.fare_to_union, wage=C.VOT_WAGE_SHARE, delay=C.FREQUENCY_DELAY_TIMED),
        "vot_low": dict(fare=table.fare_to_union, wage=C.VOT_SENSITIVITY[0], delay=C.FREQUENCY_DELAY_SHARE),
        "vot_high": dict(fare=table.fare_to_union, wage=C.VOT_SENSITIVITY[1], delay=C.FREQUENCY_DELAY_SHARE),
    }
    changed = {}
    for name, spec in scenarios.items():
        fare = spec["fare"].clip(lower=0)
        _cost, burden = trip_cost(
            fare, table.shed_median_income, table.ivt_to_union_min, table.am_headway_min, spec["wage"], spec["delay"]
        )
        changed[name] = _fare_argmax(table, burden)
    return {
        "single_gtfs_price": single,
        "flat_discount": C.FARE_FLAT_DISCOUNT,
        "percent_discount": C.FARE_PERCENT_DISCOUNT,
        "labels_changed": changed,
    }
