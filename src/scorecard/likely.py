"""Analysis 2. The primary likely constraint, measured against stations that are not held back.

The deficit on a condition is how many points a station sits below the median score of the
high-market, strong-condition stations. The largest deficit is the primary likely constraint.
A second deficit within TIE_MARGIN points is reported with it, because the evidence does not
support picking only one.
"""

import numpy as np
import pandas as pd

from . import config as C


def _deficits(frame, reference_median):
    out = pd.DataFrame(index=frame.index)
    for name in C.CONDITIONS:
        score = frame[f"{name}_score"]
        out[name] = reference_median[name] - score
    return out


def _labels(deficits):
    rows = []
    for idx, row in deficits.iterrows():
        usable = row.dropna().sort_values(ascending=False)
        positive = usable[usable > 0]
        if usable.empty or usable.iloc[0] <= 0:
            rows.append({                "primary_likely": None, "primary_deficit": np.nan, "runner_up": None, "second_likely": None,
                         "second_deficit": np.nan, "constraint_share": np.nan, "is_tie": False})
            continue
        primary = usable.index[0]
        second = usable.index[1] if len(usable) > 1 else None
        gap = usable.iloc[0] - usable.iloc[1] if second else np.inf
        share = usable.iloc[0] / positive.sum() if len(positive) else np.nan
        rows.append(
            {
                "primary_likely": primary,
                "primary_deficit": float(usable.iloc[0]),
                "runner_up": second,
                "second_likely": second if gap < C.TIE_MARGIN else None,
                "second_deficit": float(usable.iloc[1]) if second else np.nan,
                "constraint_share": float(share),
                "is_tie": bool(gap < C.TIE_MARGIN),
            }
        )
    return pd.DataFrame(rows, index=deficits.index)


def diagnose(scored):
    out = scored.copy()
    scored_rows = out["in_score"].fillna(False)
    reference = out[scored_rows & out["quadrant"].eq("market and conditions")]
    if reference.empty:
        reference = out[scored_rows & out["strong_conditions"].fillna(False)]
    ref_median = {name: reference[f"{name}_score"].median() for name in C.CONDITIONS}

    focus = out["quadrant"].eq("priority") | out["station_id"].isin(C.KITCHENER_CASE)
    deficits = _deficits(out.loc[focus], ref_median)
    # Parking does not apply where there is no scored lot, so it cannot win by being blank.
    no_lot = ~out.loc[focus, "has_scored_lot"].fillna(False)
    deficits.loc[no_lot, "parking"] = np.nan
    labels = _labels(deficits)
    for col in labels.columns:
        out.loc[focus, col] = labels[col]
    for name in C.CONDITIONS:
        out.loc[focus, f"deficit_{name}"] = deficits[name]
    out["numeric_primary"] = out["primary_likely"]

    land_use = (
        out["market_growth_rank"].ge(C.LAND_USE_GROWTH_RANK)
        & out["walk_market_rank"].le(C.LAND_USE_WALK_RANK)
        & out["quadrant"].eq("priority")
    )
    out.loc[land_use, "primary_likely"] = "land_use"
    out.loc[land_use, "is_tie"] = False
    out.loc[land_use, "second_likely"] = None

    # Same deficit measured against the station's own corridor, as a sensitivity check.
    corridor_primary = []
    for line, group in out[scored_rows].groupby("line"):
        med = {name: group[f"{name}_score"].median() for name in C.CONDITIONS}
        sub = out.index[focus & out["line"].eq(line)]
        if len(sub) == 0:
            continue
        d = _deficits(out.loc[sub], med)
        d.loc[~out.loc[sub, "has_scored_lot"].fillna(False), "parking"] = np.nan
        lab = _labels(d)
        corridor_primary.append(lab[["primary_likely"]].rename(columns={"primary_likely": "primary_vs_corridor"}))
    if corridor_primary:
        corridor = pd.concat(corridor_primary)
        out.loc[corridor.index, "primary_vs_corridor"] = corridor["primary_vs_corridor"]
    out["label_changes_with_corridor"] = out["numeric_primary"].notna() & out["primary_vs_corridor"].notna() & (
        out["numeric_primary"] != out["primary_vs_corridor"]
    )
    out["land_use_override"] = out["primary_likely"].eq("land_use") & out["numeric_primary"].notna() & out["numeric_primary"].ne("land_use")
    out.loc[focus, "confidence"] = _confidence_frame(out.loc[focus])
    out.loc[focus, "supporting_evidence"] = [_support(out.loc[i]) for i in out.index[focus]]
    out.loc[focus, "contradictory_evidence"] = [_contradict(out.loc[i]) for i in out.index[focus]]
    out.attrs["reference_median"] = ref_median
    out.attrs["reference_n"] = int(len(reference))
    return out


def confidence_label(share, is_tie, corridor_change, near_cut, land_override):
    """High only when one deficit leads, the comparison group agrees, and the station is not on the cut."""
    if land_override or (pd.notna(share) and share < C.LOW_SHARE):
        return "low"
    if is_tie or corridor_change or near_cut:
        return "medium"
    if pd.notna(share) and share >= C.CLEAR_SHARE:
        return "high"
    return "medium"


def _confidence_frame(frame):
    labels = []
    for row in frame.itertuples():
        labels.append(
            confidence_label(
                row.constraint_share,
                bool(row.is_tie) if pd.notna(row.is_tie) else False,
                bool(row.label_changes_with_corridor) if pd.notna(row.label_changes_with_corridor) else False,
                bool(row.near_cut) if pd.notna(row.near_cut) else False,
                bool(row.land_use_override) if pd.notna(row.land_use_override) else False,
            )
        )
    return labels


def _num(value, digits=0):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if number != number:
        return "n/a"
    return f"{number:,.{digits}f}"


def _count(value, singular, plural):
    text = _num(value)
    if text == "1":
        return f"1 {singular}"
    return f"{text} {plural}"


def _points(gap):
    n = abs(gap)
    word = "point" if round(n) == 1 else "points"
    return f"{n:.0f} {word}"


def _fact(row, condition):
    if condition == "service":
        return (
            f"the AM headway toward Union is {_num(row.am_headway_min)} minutes, "
            f"the longest midday gap is {_num(row.midday_max_gap_min)} minutes, "
            f"weekday service runs from {row.first_departure_clock} to {row.last_departure_clock} "
            f"({_num(row.span_hours, 1)} hours), and the weekend span averages {_num(row.weekend_span_hours, 1)} hours"
        )
    if condition == "feeder":
        return (
            f"there are {_num(row.feeder_am_arrivals)} AM-peak bus arrivals and the median wait is "
            f"{_num(row.am_transfer_wait_min)} minutes"
        )
    if condition == "walk":
        return (
            f"the walkshed holds about {_count(row.walk_pop, 'resident', 'residents')} and "
            f"{_count(row.walk_jobs, 'job', 'jobs')} "
            f"and covers {_num(100 * row.walk_reach_ratio)}% of the 800 m circle"
        )
    if condition == "parking":
        return (
            f"the 2019 lot has {_num(row.parking_spaces_2019)} spaces at {_num(100 * row.parking_utilization_2019)}% "
            f"of capacity"
        )
    if condition == "fare":
        return (
            f"the published fare is ${_num(row.fare_to_union, 2)}, the scheduled ride to Union is "
            f"{_num(row.ivt_to_union_min)} minutes, and the generalized cost at half the shed wage is "
            f"${_num(row.generalized_cost, 2)}"
        )
    return ""


def _support(row):
    if pd.isna(row.primary_likely):
        return "No condition sits below the reference median."
    if row.primary_likely == "land_use":
        text = (
            f"The housing-growth rank is {_num(row.market_growth_rank)} and the walk-catchment rank is "
            f"{_num(row.walk_market_rank)}. {_fact(row, 'walk').capitalize()}."
        )
        if pd.notna(row.numeric_primary) and row.numeric_primary != "land_use":
            label = C.CONDITION_LABELS.get(row.numeric_primary, row.numeric_primary)
            text += f" The largest score deficit is still {label.lower()}, and {_fact(row, row.numeric_primary)}."
        return text
    label = C.CONDITION_LABELS.get(row.primary_likely, row.primary_likely)
    return f"The primary label is {label.lower()}, and {_fact(row, row.primary_likely)}."


def _contradict(row):
    values = {}
    for name in C.CONDITIONS:
        value = row[f"deficit_{name}"]
        if pd.notna(value):
            values[name] = value
    if not values:
        return "I do not have a second condition to set against the label."
    name = min(values, key=values.get)
    label = C.CONDITION_LABELS.get(name, name)
    gap = values[name]
    fact = _fact(row, name)
    if gap <= 0:
        return (
            f"{label} sits {_points(gap)} above the reference median, so it argues against that label. "
            f"On that condition, {fact}."
        )
    return (
        f"No scored condition is above the reference. The smallest gap is {label.lower()}, at {_points(gap)}. "
        f"On that condition, {fact}."
    )


def evidence_frame(scored):
    """One row per priority station and Kitchener case station."""
    focus = scored["quadrant"].eq("priority") | scored["station_id"].isin(C.KITCHENER_CASE)
    rows = scored.loc[focus].copy()
    keep = [
        "station_id", "station_name", "line_name", "quadrant", "threshold_class", "near_cut",
        "market_score", "conditions_score", "conditions_gap", "primary_likely", "numeric_primary",
        "runner_up", "constraint_share", "is_tie", "confidence", "supporting_evidence",
        "contradictory_evidence", "primary_vs_corridor", "label_changes_with_corridor",
    ]
    out = rows[[c for c in keep if c in rows.columns]].sort_values(
        ["quadrant", "market_score"], ascending=[True, False]
    )
    out["primary_label"] = out["primary_likely"].map(lambda k: C.CONDITION_LABELS.get(k, k))
    out["second_label"] = out["runner_up"].map(lambda k: C.CONDITION_LABELS.get(k, "") if pd.notna(k) else "")
    return out
