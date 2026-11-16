# Where GO ridership cannot show up yet

I built this to answer one question for a Lead, Ridership Insights audience. Which GO and UP stations have a strong travel market, but weak walk access, local connections, rail service, parking headroom, or fare? I do not estimate boardings. Station ridership and PRESTO are not open, and I say so in the brief.

I scored 70 stations. 14 fall in the priority set, where the market score is at or above the median (50.7) and the conditions score is below it (48.1). Analysis 2 then names the primary likely constraint from the size of each deficit, and it flags a tie when the top two are within 10 points.

The stakeholder note is [reports/executive_brief.md](reports/executive_brief.md). The methods are in [reports/methods_note.md](reports/methods_note.md). The map is [reports/station_map.html](reports/station_map.html).

## Reproduce

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py
curl -L -o data/raw/osm/ontario.osm.pbf https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf
python scripts/run_analysis.py
```

The notebooks in `notebooks/` follow the same order I used: schedules, catchments, the quadrant, the primary likely constraint, the Kitchener line, the transfer audit, and the recommendations. They read the tables written by `scripts/run_analysis.py`.

Sources and licences are in [data/SOURCES.md](data/SOURCES.md).
