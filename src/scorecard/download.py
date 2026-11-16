"""Download every raw input. Files that already exist are skipped, so the script is safe to rerun."""

import zipfile

import duckdb
import requests

from . import config as C

GO_GTFS = "https://assets.metrolinx.com/raw/upload/Documents/Metrolinx/Open%20Data/GO-GTFS.zip"
UP_GTFS = "https://assets.metrolinx.com/raw/upload/Documents/Metrolinx/Open%20Data/UP-GTFS.zip"
PARKING_2019 = (
    "https://assets.metrolinx.com/raw/upload/v1662043582/Documents/Metrolinx/Open%20Data/"
    "201912_Parking_By_Facility_All.csv"
)

# Mobility Database identifiers for the latest published feed of each local agency.
LOCAL_FEEDS = {
    "barrie": "mdb-3",
    "brampton": "mdb-1994",
    "burlington": "mdb-724",
    "durham": "mdb-726",
    "grt_bus": "mdb-3150",
    "grt_ion": "mdb-3151",
    "guelph": "mdb-3140",
    "hsr": "mdb-2618",
    "milton": "mdb-759",
    "miway": "mdb-730",
    "niagara": "tld-859",
    "oakville": "mdb-725",
    "ttc": "mdb-732",
    "yrt": "mdb-728",
}

STATCAN_TABLES = {
    # Jobs by census tract of work (employed labour force with a usual place of work).
    "t98100498.zip": "https://www150.statcan.gc.ca/n1/tbl/csv/98100498-eng.zip",
    # Commuting flows from census subdivision of residence to census subdivision of work.
    "t98100459.zip": "https://www150.statcan.gc.ca/n1/tbl/csv/98100459-eng.zip",
}
# Statistics Canada Census Profile and boundary files, republished unmodified as Parquet by
# Data for Canada on Source Cooperative. I use this copy because the www12 StatCan file
# server blocks scripted downloads behind a browser check.
D4C = (
    "https://data.source.coop/dataforcanada/d4c-datapkg-statistical/processed/"
    "ca_statcan_2021A000011124_d4c-datapkg-statistical_{name}_2021_v0.1.0-beta.parquet"
)

# Census Profile characteristic IDs used in the analysis. These follow the CHARACTERISTIC_ID
# numbering of the official Census Profile CSV (98-401-X2021), which I verify against the
# economic-region profile file in notebook 00. The SDMX API codelist numbers differ.
PROFILE_ID_CHECK = "https://zenodo.org/records/15333781/files/98-401-X2021008_eng_CSV.zip?download=1"
DA_CHARACTERISTICS = {
    1: "pop_2021",
    4: "private_dwellings",
    7: "land_area_km2",
    243: "median_household_income",
    1440: "occupied_dwellings_by_period",
    1448: "dwellings_built_2016_2021",
    2593: "employed_total_pow",
    2594: "worked_at_home",
    2597: "usual_place_of_work",
    2603: "commuters_total",
    2604: "commute_car",
    2607: "commute_transit",
    2608: "commute_walk",
}


def _get(url, dest, timeout=600):
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip   {dest.name}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": "go-station-scorecard"}) as r:
        r.raise_for_status()
        tmp = dest.with_suffix(dest.suffix + ".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
        tmp.rename(dest)
    print(f"fetch  {dest.name}  {dest.stat().st_size / 1e6:.1f} MB")
    return dest


def download_transit():
    _get(GO_GTFS, C.RAW / "GO-GTFS.zip")
    _get(UP_GTFS, C.RAW / "UP-GTFS.zip")
    _get(PARKING_2019, C.RAW / "parking_201912.csv")
    for name, feed_id in LOCAL_FEEDS.items():
        _get(f"https://files.mobilitydatabase.org/{feed_id}/latest.zip", C.RAW / "local_gtfs" / f"{name}.zip")


def download_census_tables():
    for fname, url in STATCAN_TABLES.items():
        _get(url, C.CENSUS_DIR / fname, timeout=1800)
    _get(PROFILE_ID_CHECK, C.CENSUS_DIR / "98-401-X2021008_eng_CSV.zip")


def _bbox_filter():
    b = C.STUDY_BBOX
    return (
        f"geom_bbox.xmax >= {b['xmin']} AND geom_bbox.xmin <= {b['xmax']} "
        f"AND geom_bbox.ymax >= {b['ymin']} AND geom_bbox.ymin <= {b['ymax']}"
    )


def download_census_geography():
    """Pull only the study-area rows from the national Parquet files."""
    out = C.CENSUS_DIR
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")

    targets = {
        "da_boundaries.parquet": (
            "dissemination_areas_cartographic",
            "da_dguid, ct_dguid, csd_dguid, csd_name, cma_name",
        ),
        "ct_boundaries.parquet": ("census_tracts_cartographic", "ct_dguid, cma_name"),
        "csd_boundaries.parquet": ("census_subdivisions_cartographic", "csd_dguid, csd_name, csd_type, cd_name"),
    }
    for fname, (name, cols) in targets.items():
        dest = out / fname
        if dest.exists():
            print(f"skip   {fname}")
            continue
        url = D4C.format(name=name)
        con.execute(
            f"""COPY (SELECT {cols}, ST_AsWKB(geom) AS geometry FROM read_parquet('{url}')
                WHERE pr_dguid = '2021A000235' AND {_bbox_filter()})
                TO '{dest}' (FORMAT PARQUET)"""
        )
        print(f"fetch  {fname}")

    dest = out / "da_profile.parquet"
    if dest.exists():
        print("skip   da_profile.parquet")
    else:
        url = D4C.format(name="census_pop_dissemination_areas")
        select = ", ".join(f"count_total_{k} AS {v}" for k, v in DA_CHARACTERISTICS.items())
        con.execute(
            f"""COPY (SELECT da_dguid, {select} FROM read_parquet('{url}')
                WHERE da_dguid LIKE '2021S051235%') TO '{dest}' (FORMAT PARQUET)"""
        )
        print("fetch  da_profile.parquet")


def extract_gtfs():
    """Unzip every GTFS feed into data/interim/gtfs/<name>/."""
    feeds = {"go": C.RAW / "GO-GTFS.zip", "up": C.RAW / "UP-GTFS.zip"}
    feeds.update({p.stem: p for p in sorted((C.RAW / "local_gtfs").glob("*.zip"))})
    for name, path in feeds.items():
        target = C.GTFS_DIR / name
        if (target / "stop_times.txt").exists():
            continue
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as z:
            z.extractall(target)
        print(f"unzip  {name}")


def download_all():
    download_transit()
    download_census_tables()
    download_census_geography()
    extract_gtfs()
