"""Join service, access, parking, fares and census catchments into one station table."""

import geopandas as gpd
import numpy as np
import pandas as pd

from . import catchments, census, config as C

COUNT_COLS = [
    "pop_2021",
    "private_dwellings",
    "occupied_dwellings_by_period",
    "dwellings_built_2016_2021",
    "employed_total_pow",
    "worked_at_home",
    "usual_place_of_work",
    "commuters_total",
    "commute_car",
    "commute_transit",
    "commute_walk",
]


def primary_line(lines):
    parts = [p for p in str(lines).split(",") if p and p != "UP"]
    return parts[0] if parts else "UP"


def _income(zones, das, zone_id="station_id"):
    """Population-weighted average of dissemination-area median household incomes.

    A median cannot be area-weighted directly. Weighting each DA median by the
    population that falls inside the zone is the workable approximation, and I
    treat it as that, not as a true median.
    """
    units = das.copy()
    units["unit_area"] = units.geometry.area
    pieces = gpd.overlay(zones[[zone_id, "geometry"]], units, how="intersection", keep_geom_type=True)
    share = pieces.geometry.area / pieces.unit_area
    weight = pieces["pop_2021"].fillna(0) * share
    income = pieces["median_household_income"]
    ok = income.notna() & (weight > 0)
    num = (income[ok] * weight[ok]).groupby(pieces.loc[ok, zone_id]).sum()
    den = weight[ok].groupby(pieces.loc[ok, zone_id]).sum()
    return (num / den).rename("median_household_income")


def _zone_counts(zones, das, jobs, prefix):
    weighted = catchments.area_weight(zones, das, COUNT_COLS)
    job_w = catchments.area_weight(zones, jobs, ["jobs"])
    out = weighted.merge(job_w, on="station_id", how="left")
    out["jobs"] = out["jobs"].fillna(0)
    keep = {
        "station_id": "station_id",
        "pop_2021": f"{prefix}_pop",
        "jobs": f"{prefix}_jobs",
        "dwellings_built_2016_2021": f"{prefix}_new_dwellings",
        "occupied_dwellings_by_period": f"{prefix}_dwellings",
        "employed_total_pow": f"{prefix}_employed",
        "worked_at_home": f"{prefix}_wfh",
        "commuters_total": f"{prefix}_commuters",
        "commute_transit": f"{prefix}_transit_commuters",
        "commute_walk": f"{prefix}_walk_commuters",
    }
    out = out[list(keep)].rename(columns=keep)
    out[f"{prefix}_pop_jobs"] = out[f"{prefix}_pop"] + out[f"{prefix}_jobs"]
    out[f"{prefix}_new_dwelling_share"] = np.where(
        out[f"{prefix}_dwellings"] > 0, out[f"{prefix}_new_dwellings"] / out[f"{prefix}_dwellings"], np.nan
    )
    out[f"{prefix}_wfh_share"] = np.where(
        out[f"{prefix}_employed"] > 0, out[f"{prefix}_wfh"] / out[f"{prefix}_employed"], np.nan
    )
    return out


def trip_cost(fare, income, ivt_min, headway_min, wage_share, delay_share):
    """Generalized cost of one scheduled trip to Union, and that cost per $10,000 of income.

    Cost is the published fare plus the value of in-vehicle time and frequency delay.
    The value of time is `wage_share` of the shed median household income, spread over
    ANNUAL_HOURS. Frequency delay is `delay_share` of the AM-peak headway.
    """
    fare = pd.Series(fare, dtype="float64")
    income = pd.Series(income, dtype="float64")
    ivt_min = pd.Series(ivt_min, dtype="float64")
    headway_min = pd.Series(headway_min, dtype="float64")
    vot_per_min = wage_share * income / C.ANNUAL_HOURS / 60.0
    cost = fare + vot_per_min * (ivt_min + delay_share * headway_min)
    burden = cost / income * 10000
    usable = income.gt(0) & fare.notna() & ivt_min.notna() & headway_min.notna()
    return cost.where(usable), burden.where(usable)


def am_transfer_waits(waits):
    """Median scheduled bus-to-train wait in the weekday AM peak, in minutes."""
    if waits.empty:
        return pd.DataFrame(columns=["station_id", "am_transfer_wait_min", "am_transfer_n"])
    am = waits[(waits.direction == "bus_to_train") & waits.event_sec.between(C.AM_PEAK[0], C.AM_PEAK[1])].copy()
    g = am.groupby("station_id").wait_sec
    return pd.DataFrame(
        {"am_transfer_wait_min": g.median() / 60, "am_transfer_n": g.size()}
    ).reset_index()


def build(stations, service, fares, feeders, waits, park):
    da_b, ct_b, csd_b = catchments.load_census_geography()
    profile = census.da_profile()
    das = da_b.merge(profile, on="da_dguid", how="left")
    jobs = ct_b.merge(census.jobs_by_ct(), on="ct_dguid", how="left")
    jobs["jobs"] = jobs["jobs"].fillna(0)

    walks = catchments.build_walksheds(stations)
    sheds = catchments.build_station_sheds(stations)
    walk_counts = _zone_counts(walks, das, jobs, "walk")
    shed_counts = _zone_counts(sheds, das, jobs, "shed")
    walk_income = _income(walks, das)
    shed_income = _income(sheds, das).rename("shed_median_income")

    points = stations.to_crs(C.CRS_METRIC)
    csd_hit = gpd.sjoin(points[["station_id", "geometry"]], csd_b[["csd_dguid", "csd_name", "geometry"]], predicate="within")
    csd_hit = csd_hit.drop_duplicates("station_id")[["station_id", "csd_dguid", "csd_name"]]
    flows = census.commute_to_toronto(census.ontario_flows())

    base = stations.drop(columns="geometry").merge(service, on="station_id", how="left")
    base["line"] = base.lines.map(primary_line)
    base["line_name"] = base.line.map(C.LINE_NAMES)
    fare_cols = ["station_id", "fare_to_union"]
    for extra in ("fare_to_union_high", "fare_product_n"):
        if extra in fares.columns:
            fare_cols.append(extra)
    base = base.merge(fares[fare_cols], on="station_id", how="left")
    base = base.merge(feeders, on="station_id", how="left")
    for col in ["feeder_am_arrivals", "feeder_day_arrivals", "feeder_routes"]:
        base[col] = base[col].fillna(0)
    base = base.merge(am_transfer_waits(waits), on="station_id", how="left")
    base = base.merge(park, on="station_id", how="left")
    base = base.merge(walk_counts, on="station_id", how="left")
    base = base.merge(walks.drop(columns="geometry"), on="station_id", how="left")
    base = base.merge(shed_counts, on="station_id", how="left")
    base = base.merge(shed_income, on="station_id", how="left")
    base = base.merge(walk_income, on="station_id", how="left")
    base = base.merge(csd_hit, on="station_id", how="left")
    base = base.merge(flows, on="csd_dguid", how="left")

    base["jobs_per_resident_walk"] = np.where(base.walk_pop > 0, base.walk_jobs / base.walk_pop, np.inf)
    base["role"] = np.where(base.jobs_per_resident_walk >= C.DESTINATION_JOBS_TO_POP, "destination", "origin")
    base["has_scored_lot"] = base.parking_spaces_2019.fillna(0).ge(C.PARKING_MIN_SPACES) & base.role.eq("origin")
    util = base.parking_utilization_2019.clip(upper=1)
    base["parking_headroom"] = np.where(base.has_scored_lot, 1 - util, np.nan)
    base["sticker_burden"] = np.where(
        base.shed_median_income > 0, base.fare_to_union / base.shed_median_income * 10000, np.nan
    )
    base["generalized_cost"], base["fare_burden"] = trip_cost(
        base.fare_to_union,
        base.shed_median_income,
        base.ivt_to_union_min,
        base.am_headway_min,
        C.VOT_WAGE_SHARE,
        C.FREQUENCY_DELAY_SHARE,
    )
    base["excluded_reason"] = base.station_id.map(C.EXCLUDED)
    base["in_score"] = base.excluded_reason.isna()
    return base, walks, sheds
