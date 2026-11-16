# Sources

I downloaded these files on 15 November 2026. Raw files are not in git, because several of them are large. `scripts/download_data.py` fetches them again, except the Ontario OpenStreetMap extract, which I download separately and document here.

| Input | What I use it for | Source | Licence |
| --- | --- | --- | --- |
| GO-GTFS.zip | Rail stations, Wednesday 18 Nov 2026 service, Saturday and Sunday service, fare from each zone to Union | Metrolinx Open Data, GO Transit GTFS | Open Government Licence – Ontario – Metrolinx |
| UP-GTFS.zip | UP Express stations and service on the same dates | Metrolinx Open Data, UP Express GTFS | Open Government Licence – Ontario – Metrolinx |
| 201912_Parking_By_Facility_All.csv | 2019 lot capacity and weekday occupancy | Metrolinx Open Data, GO Rail Parking and Utilization | Open Government Licence – Ontario – Metrolinx |
| Local GTFS, 14 agencies | Stops within 250 m of a station, AM-peak arrivals, scheduled transfer waits | Mobility Database `latest.zip` for each feed id in `src/scorecard/download.py` | Each agency's own open-data licence, named in the feed |
| Census Profile characteristics at dissemination area | Population, dwellings built 2016 to 2021, income, work from home, commute mode | Statistics Canada 2021 Census Profile, via the Data for Canada Parquet republication of 98-401-X2021 | Open Government Licence – Canada. The Parquet copy is unmodified values, not an official Statistics Canada product |
| Dissemination area, tract and subdivision boundaries | Catchments | Statistics Canada 2021 cartographic boundary files, same Parquet republication, study-area rows only | Open Government Licence – Canada |
| Table 98-10-0498 | Jobs by census tract of work, usual place of work | Statistics Canada, 15 Nov 2023 release | Open Government Licence – Canada |
| Table 98-10-0459 | Commuting flows between census subdivisions | Statistics Canada | Open Government Licence – Canada |
| 98-401-X2021008 | Check that the characteristic IDs I use match the official Census Profile labels | Statistics Canada Census Profile, economic regions file, mirrored on Zenodo record 15333781 | Open Government Licence – Canada |
| ontario-latest.osm.pbf | Walking network for the 800 m walksheds | Geofabrik, Ontario extract | Open Database Licence |

The Census Profile Parquet files are published by Data for Canada on Source Cooperative. I checked the characteristic IDs against the official Census Profile CSV before using them. Statistics Canada does not endorse that republication.

I do not use station-level GO ridership or PRESTO. Those series are not on the open-data page, and this project does not estimate boardings.
