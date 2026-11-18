"""Turn a primary likely constraint into an action, an owner and a measure."""

import pandas as pd

from . import config as C

ACTIONS = {
    "service": {
        "action": "Add off-peak and weekend rail trips before adding more peak trains. The market is already there, and the timetable is the thin condition.",
        "owner": "Metrolinx service planning",
        "cost": "High",
        "timing": "Next service change",
        "kpi": "Off-peak and weekend boardings at the station, against another station on the same line",
    },
    "feeder": {
        "action": "Add AM-peak bus arrivals and shorten the scheduled wait to the train, with the municipal operator that already serves the station.",
        "owner": "Municipal transit agency, through the Metrolinx relationship owner",
        "cost": "Low",
        "timing": "Next local schedule change",
        "kpi": "Median scheduled bus-to-train wait in the AM peak, then boardings once ridership is available",
    },
    "walk": {
        "action": "Treat walk access as the constraint. More trains will not reach people who cannot get to the platform on foot.",
        "owner": "Metrolinx station access, with the municipality",
        "cost": "Medium",
        "timing": "1 to 3 years",
        "kpi": "Population and jobs inside the 800 m walkshed after the connection opens",
    },
    "parking": {
        "action": "The 2019 lot was already full on a normal weekday. Do not plan peak ridership growth on more parking spaces until occupancy is measured again.",
        "owner": "Metrolinx station access",
        "cost": "Medium",
        "timing": "Re-measure before the next parking decision",
        "kpi": "Weekday peak occupancy, and the share of riders arriving by local transit",
    },
    "fare": {
        "action": "The generalized cost of a scheduled trip to Union is high relative to household income around the station. That cost is the published fare plus the value of in-vehicle time and frequency delay. Review the fare product before adding service that those households may not buy.",
        "owner": "Metrolinx fare policy",
        "cost": "Low",
        "timing": "Next fare review",
        "kpi": "Generalized cost of a trip to Union as a share of median household income in the station shed",
    },
    "land_use": {
        "action": "Current population and jobs inside the walk are thin, and the market score is carried by recent housing growth. I would treat this as a land-use question, not as a near-term service add.",
        "owner": "Municipal planning",
        "cost": "High",
        "timing": "Municipal planning horizon",
        "kpi": "People and jobs per hectare inside the 800 m walkshed",
    },
}


def build(scored):
    rows = scored[scored["quadrant"].eq("priority") | scored["station_id"].isin(C.KITCHENER_CASE)].copy()
    records = []
    for r in rows.itertuples():
        key = r.primary_likely
        spec = ACTIONS.get(key, {})
        owner = spec.get("owner", "")
        if key == "feeder" and isinstance(r.main_feeder_agency, str):
            owner = f"{C.LOCAL_AGENCIES.get(r.main_feeder_agency, r.main_feeder_agency)}, with Metrolinx"
        action = spec.get("action", "")
        if r.is_tie and r.second_likely in ACTIONS:
            action = (
                f"The top two gaps are close, so I would test {C.CONDITION_LABELS.get(key, key).lower()} first "
                f"and keep {C.CONDITION_LABELS.get(r.second_likely, r.second_likely).lower()} as the alternative. "
                + action
            )
        records.append(
            {
                "station_id": r.station_id,
                "station_name": r.station_name,
                "line_name": r.line_name,
                "quadrant": r.quadrant,
                "market_score": round(r.market_score, 1),
                "conditions_score": round(r.conditions_score, 1),
                "primary_likely": C.CONDITION_LABELS.get(key, key),
                "largest_deficit": C.CONDITION_LABELS.get(r.numeric_primary, ""),
                "constraint_share": None if pd.isna(r.constraint_share) else round(100 * r.constraint_share, 0),
                "is_tie": bool(r.is_tie) if key != "land_use" else False,
                "second_constraint": "" if key == "land_use" else C.CONDITION_LABELS.get(r.second_likely, ""),
                "corridor_constraint": C.CONDITION_LABELS.get(r.primary_vs_corridor, ""),
                "recommended_action": action,
                "owner": owner,
                "relative_cost": spec.get("cost", ""),
                "timing": spec.get("timing", ""),
                "kpi": spec.get("kpi", ""),
                "label_changes_with_corridor": bool(r.label_changes_with_corridor),
            }
        )
    return pd.DataFrame(records).sort_values(["quadrant", "market_score"], ascending=[True, False])
