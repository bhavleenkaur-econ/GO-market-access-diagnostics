"""Project settings. Every weight, threshold and date used in the analysis lives here."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
SQL = ROOT / "sql"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

GTFS_DIR = INTERIM / "gtfs"
OSM_CACHE = INTERIM / "osm"
CENSUS_DIR = RAW / "census"

# Coordinate reference system for distance and area work (NAD83 / Statistics Canada Lambert).
CRS_METRIC = "EPSG:3347"
CRS_WGS84 = "EPSG:4326"

# Study area: every GO rail station plus a margin wide enough for a 10 km station shed.
STUDY_BBOX = {"xmin": -80.75, "ymin": 42.95, "xmax": -78.55, "ymax": 44.55}

# Service dates. GO publishes service by calendar date, so I pick one ordinary Wednesday
# and one Saturday inside the current feed window.
GO_WEEKDAY = "20261118"
GO_SATURDAY = "20261121"
GO_SUNDAY = "20261122"

# Time bands, in seconds after midnight.
AM_PEAK = (6 * 3600, 9 * 3600)
MIDDAY = (9 * 3600 + 30 * 60, 15 * 3600)
PM_PEAK = (15 * 3600 + 30 * 60, 18 * 3600 + 30 * 60)
EVENING = (19 * 3600, 28 * 3600)

# Catchments.
WALK_DISTANCE_M = 800
WALK_EDGE_BUFFER_M = 60
SHED_CAP_M = 10_000
FEEDER_RADIUS_M = 250
MIN_TRANSFER_S = 3 * 60

# Stations excluded from scoring, with the reason recorded in the methods note.
EXCLUDED = {
    "UN": "Union Station is the network destination, so I score it as a destination and keep it out of the origin ranking.",
    "SF": "Stratford is outside the tracted census area and runs a handful of pilot trips, so the job and service measures are not comparable.",
}

# Local transit agencies that feed GO stations. Keys match the files in data/raw/local_gtfs.
LOCAL_AGENCIES = {
    "barrie": "Barrie Transit",
    "brampton": "Brampton Transit",
    "burlington": "Burlington Transit",
    "durham": "Durham Region Transit",
    "grt_bus": "Grand River Transit",
    "grt_ion": "Grand River Transit ION",
    "guelph": "Guelph Transit",
    "hsr": "Hamilton Street Railway",
    "milton": "Milton Transit",
    "miway": "MiWay",
    "niagara": "Niagara Region Transit",
    "oakville": "Oakville Transit",
    "ttc": "Toronto Transit Commission",
    "yrt": "York Region Transit",
}

LINE_NAMES = {
    "BR": "Barrie",
    "KI": "Kitchener",
    "LE": "Lakeshore East",
    "LW": "Lakeshore West",
    "MI": "Milton",
    "RH": "Richmond Hill",
    "ST": "Stouffville",
    "UP": "UP Express",
}

# Toronto census subdivision, the main commute destination for the GO network.
TORONTO_CSD_NAME = "Toronto (C), Ont."

# Analysis 1, the quadrant. Scores are percentile ranks from 0 to 100.
MARKET_COMPONENTS = ["shed_pop_jobs", "commute_to_toronto_share", "recent_dwelling_share"]
CONDITIONS = ["service", "feeder", "walk", "parking", "fare"]
CONDITION_LABELS = {
    "service": "Rail service",
    "feeder": "Local connections",
    "walk": "Walk access",
    "parking": "Parking headroom",
    "fare": "Fare burden",
    "land_use": "Land use",
}
WEIGHT_SCHEMES = {
    "equal": {"service": 1, "feeder": 1, "walk": 1, "parking": 1, "fare": 1},
    "access_heavy": {"service": 1, "feeder": 2, "walk": 2, "parking": 2, "fare": 1},
    "service_heavy": {"service": 2, "feeder": 1, "walk": 1, "parking": 1, "fare": 1},
}
PRIMARY_SCHEME = "equal"

# A 2019 lot is treated as full at or above this mean weekday occupancy.
# Lots smaller than PARKING_MIN_SPACES are recorded but not scored. A 2-space lot being
# "full" is not a commuter constraint. Guelph Central's 18 spaces are discussed in the
# corridor chapter, where the small lot is the point, rather than in the network score.
PARKING_FULL_UTILIZATION = 0.95
PARKING_MIN_SPACES = 50

# Stations in the Kitchener corridor chapter.
KITCHENER_CASE = ["KI", "GL", "AC", "GE", "MO", "BR", "BE"]

# Analysis 2, the primary likely constraint.
TIE_MARGIN = 10
CLEAR_SHARE = 0.5
LOW_SHARE = 0.35
LAND_USE_GROWTH_RANK = 67
LAND_USE_WALK_RANK = 33

# A station within this many points of either median is too close to the cut to treat as a firm class.
NEAR_CUT_POINTS = 5

# Generalized cost. The value of time is a share of the shed's median household income,
# spread over a full-time year. It is a stated assumption, not a measured wage.
ANNUAL_HOURS = 2080
VOT_WAGE_SHARE = 0.5
VOT_SENSITIVITY = (0.35, 0.70)
# Half the headway is the wait if the passenger does not time the arrival.
# A quarter of the headway is the allowance if the passenger knows the timetable.
FREQUENCY_DELAY_SHARE = 0.5
FREQUENCY_DELAY_TIMED = 0.25
# The GTFS fare file has one price per zone pair. These two reductions are a sensitivity,
# not a published PRESTO tariff.
FARE_FLAT_DISCOUNT = 1.0
FARE_PERCENT_DISCOUNT = 0.10

# Destination-leaning stations have more jobs than residents inside the walkshed.
DESTINATION_JOBS_TO_POP = 1.0
