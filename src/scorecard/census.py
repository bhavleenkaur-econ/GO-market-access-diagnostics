"""Census inputs: dissemination-area profile, jobs by census tract of work, and commuting flows."""

import zipfile

import pandas as pd

from . import config as C
from .download import DA_CHARACTERISTICS


def verify_profile_ids():
    """Check the characteristic IDs I use against the official Census Profile CSV labels."""
    z = zipfile.ZipFile(C.CENSUS_DIR / "98-401-X2021008_eng_CSV.zip")
    name = next(n for n in z.namelist() if n.endswith("CSV_data.csv"))
    ref = pd.read_csv(z.open(name), encoding="latin-1", usecols=["CHARACTERISTIC_ID", "CHARACTERISTIC_NAME"], nrows=2631)
    ref = ref.set_index("CHARACTERISTIC_ID").CHARACTERISTIC_NAME.str.strip()
    return pd.DataFrame(
        [{"id": k, "column": v, "official_label": ref.get(k)} for k, v in DA_CHARACTERISTICS.items()]
    )


def da_profile():
    return pd.read_parquet(C.CENSUS_DIR / "da_profile.parquet")


def jobs_by_ct():
    """Employed labour force with a usual place of work, by census tract of work (table 98-10-0498)."""
    z = zipfile.ZipFile(C.CENSUS_DIR / "t98100498.zip")
    df = pd.read_csv(z.open("98100498.csv"), dtype=str)
    total_col = next(c for c in df.columns if c.startswith("Employment income groups (18):Total"))
    df = df[df["Place of work status (3)"] == "Usual place of work"]
    out = df[["DGUID", total_col]].rename(columns={"DGUID": "ct_dguid", total_col: "jobs"})
    out["jobs"] = pd.to_numeric(out.jobs, errors="coerce").fillna(0)
    return out[out.ct_dguid.str.startswith("2021S0507")]


def ontario_flows():
    """Workers by census subdivision of residence and of work, Ontario residents only (table 98-10-0459).

    The source CSV is 2.2 GB, so I stream it in chunks and keep only Ontario origins.
    The result is cached as a small Parquet file.
    """
    cache = C.INTERIM / "ontario_commute_flows.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    z = zipfile.ZipFile(C.CENSUS_DIR / "t98100459.zip")
    total_col = "Gender (3):Total - Gender[1]"
    parts = []
    reader = pd.read_csv(
        z.open("98100459.csv"), usecols=["GEO", "DGUID", "Place of work", total_col], dtype=str, chunksize=500_000
    )
    for chunk in reader:
        chunk = chunk[chunk.DGUID.str.startswith("2021A000535")]
        chunk = chunk.assign(workers=pd.to_numeric(chunk[total_col], errors="coerce").fillna(0))
        parts.append(chunk[chunk.workers > 0][["GEO", "DGUID", "Place of work", "workers"]])
    flows = pd.concat(parts, ignore_index=True).rename(
        columns={"GEO": "home_csd_name", "DGUID": "home_csd_dguid", "Place of work": "work_csd"}
    )
    flows.to_parquet(cache)
    return flows


def commute_to_toronto(flows):
    """Share of each home CSD's commuters whose usual place of work is the City of Toronto."""
    g = flows.groupby("home_csd_dguid")
    total = g.workers.sum()
    to_tor = flows[flows.work_csd == C.TORONTO_CSD_NAME].groupby("home_csd_dguid").workers.sum()
    out = pd.DataFrame({"csd_workers": total, "to_toronto": to_tor}).fillna(0)
    out["commute_to_toronto_share"] = out.to_toronto / out.csd_workers
    return out.reset_index().rename(columns={"home_csd_dguid": "csd_dguid"})
