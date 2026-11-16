"""2019 GO Rail parking capacity and utilization (Metrolinx open data, December 2019 extract)."""

import pandas as pd

from . import config as C

# 2019 facility ID to current GTFS station code. Written out in full so every match can be checked.
FACILITY_TO_STATION = {
    "ADGO": "AD", "AUGO": "AU", "BSGO": "BA", "BDGO": "BD", "GWIL": "EA", "KGGO": "KC", "MAGO": "MP",
    "NMGO": "NE", "RUGO": "RU", "ATGO": "AC", "BLGO": "BE", "BRGO": "BR", "ETGO": "ET", "GEGO": "GE",
    "GUEP": "GL", "MTGO": "MA", "MPGO": "MO", "WSGO": "WE", "AJGO": "AJ", "DAGO": "DA", "EGGO": "EG",
    "GUGO": "GU", "OSGO": "OS", "PKGO": "PIN", "ROGO": "RO", "SCGO": "SC", "WHGO": "WH", "ALGO": "AL",
    "APGO": "AP", "BTGO": "BO", "BUGO": "BU", "CLGO": "CL", "EXGO": "EX", "HMGO": "HA", "LBGO": "LO",
    "MMGO": "MI", "OKGO": "OA", "PCGO": "PO", "CKGO": "CO", "DXGO": "DI", "ERGO": "ER", "LGGO": "LS",
    "MDGO": "ME", "MNGO": "ML", "STGO": "SR", "GORL": "GO", "LNGO": "LA", "CMGO": "OL", "ORGO": "OR",
    "RHGO": "RI", "AGGO": "AG", "CEGO": "CE", "LCGO": "LI", "MKGO": "MR", "MIGO": "MK", "MJGO": "MJ",
    "SVGO": "ST", "UVGO": "UI",
}

MONTHS_2019 = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV"]

QA_NOTES = [
    "Lincolnville GO is now Old Elm GO, Oshawa GO is now Durham College Oshawa GO, and Brampton GO is now "
    "Brampton Innovation District GO. I matched them by facility ID.",
    "A 46-space row filed under the Lakeshore West corridor carries the Whitby facility ID (WHGO). Whitby's "
    "3,632-space lot is reported on the Lakeshore East row, so I could not attribute the extra row and dropped it.",
    "Months recorded as zero are treated as missing counts, not empty lots, because they appear mid-year at "
    "stations that were otherwise full.",
    "Mount Dennis, Confederation, Bloomington, Kennedy, Kipling, Bloor, Downsview Park, Kitchener, West Harbour, "
    "Niagara Falls, St. Catharines and Pearson have no 2019 commuter lot in the file. I score parking as not "
    "applicable at those stations rather than as a weakness.",
]


def load():
    raw = pd.read_csv(C.RAW / "parking_201912.csv", skiprows=1, thousands=",")
    raw = raw[raw["Facility ID"].isin(FACILITY_TO_STATION)]
    raw = raw[~((raw["Facility ID"] == "WHGO") & (raw["Corridor"] == "Lakeshore West Rail Line"))]
    months = [f"{m} 2019" for m in MONTHS_2019]
    occ = raw[months].apply(pd.to_numeric, errors="coerce").where(lambda d: d > 0)
    out = pd.DataFrame(
        {
            "station_id": raw["Facility ID"].map(FACILITY_TO_STATION),
            "facility_id_2019": raw["Facility ID"],
            "parking_spaces_2019": raw["Capacity DEC 2019"].astype(float),
            "parking_mean_occupied_2019": occ.mean(axis=1),
            "parking_peak_month_occupied_2019": occ.max(axis=1),
        }
    )
    out["parking_utilization_2019"] = out.parking_mean_occupied_2019 / out.parking_spaces_2019
    out["parking_full_2019"] = out.parking_utilization_2019 >= C.PARKING_FULL_UTILIZATION
    return out.reset_index(drop=True)
