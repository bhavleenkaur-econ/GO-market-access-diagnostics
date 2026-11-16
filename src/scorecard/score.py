"""Analysis 1. Market potential against enabling conditions, as percentile scores.

A higher score is better. Parking is left blank where there is no commuter lot, and the
condition average is renormalized over the conditions that apply.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from . import config as C


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

    out.loc[idx, "service_score"] = _blend(out.loc[idx], ["weekday_departures", "offpeak_weekend_departures"])

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
