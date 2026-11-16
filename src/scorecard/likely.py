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
            rows.append({"primary_likely": None, "primary_deficit": np.nan, "second_likely": None,
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
    out.attrs["reference_median"] = ref_median
    out.attrs["reference_n"] = int(len(reference))
    return out
