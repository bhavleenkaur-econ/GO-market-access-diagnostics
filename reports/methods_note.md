# Methods note

I wrote this so a reader can rerun the scorecard and see where each judgement comes from. The code is in `src/scorecard/`, and the SQL is in `sql/`. Settings, weights, and thresholds are in `src/scorecard/config.py`.

## Objective

I wanted to know where a GO or UP station has a travel market that the current access and service conditions are not set up to serve. I did not estimate ridership. Open data does not include station boardings or PRESTO, and I would rather say that than fit a model to a 2019 PDF.

## Order of work

1. I downloaded GO and UP Express GTFS, 14 local GTFS feeds, the December 2019 parking file, census geography and profile values, commuting flows, jobs by place of work, and the Geofabrik Ontario OpenStreetMap extract.
2. I counted rail trips in DuckDB for one Wednesday, one Saturday, and one Sunday in the current GO feed.
3. I counted local-bus arrivals within 250 m and the scheduled wait to the next train toward Union.
4. I built an 800 m walkshed on the walking network, and a 10 km station shed.
5. I apportioned census counts into those catchments by area.
6. I scored market and conditions, split stations at the median, and then measured which condition sits furthest below the stations that are not held back.

## Service

GO publishes service by calendar date, not by a weekly calendar. I used Wednesday 18 November 2026, Saturday 21 November 2026, and Sunday 22 November 2026. All three dates are marked as service in the feed. A departure is a stop event where the passenger can board. Peak trips toward Union are weekday departures between 06:00 and 09:00 on trips that reach Union later in the same trip.

Local feeds are not on the same calendar. For each agency I took the Wednesday in the feed with the most trips, and I recorded that date in `data/processed/feeder_service_dates.csv`. Guelph Transit's feed, for example, is an older schedule than the November GO feed. The connection analysis uses each operator's own representative weekday.

## Catchments

The walkshed is the set of walking streets within 800 m network distance of the station, buffered by 60 m so it can be overlaid on census areas. Walk reach is that area divided by the area of an 800 m circle. A station behind a highway scores lower than a station on a grid.

The Geofabrik extract does not carry from-node and to-node ids. I join the walking network at every vertex, rounded to one metre, so a street that meets another street in the middle is connected. At the station I start the walk on the largest connected piece within 150 m. A short platform path is often the nearest segment, and using it would shrink the walkshed to that path.

The station shed is the Voronoi cell around the station, cut at 10 km. It is a stand-in for the drive and local-transit market, not a surveyed catchment.

Census counts are area-weighted. Household income is a population-weighted average of dissemination-area medians, because a median cannot be split by area. Jobs are usual-place-of-work counts from table 98-10-0498, area-weighted from census tracts. The Toronto commute share is from table 98-10-0459 and is a property of the census subdivision the station sits in, not of the walkshed.

## Scores

I rank each input from 0 to 100 among the stations I score. Higher is better.

Market score, equal weight:

- people plus jobs in the station shed
- share of the home municipality's commuters whose usual workplace is Toronto
- share of occupied dwellings built from 2016 to 2021

Work from home is reported beside the score. I do not subtract it from the market. A high work-from-home share changes what kind of service I would recommend, toward span and weekend, rather than making the market look small.

Conditions score, equal weight, with two other weightings as a check:

- Rail service: weekday departures and off-peak plus weekend departures
- Local connections: AM-peak bus arrivals, and the median AM-peak scheduled wait, reversed so a long wait scores low
- Walk access: people plus jobs in the walkshed, and walk reach
- Parking headroom: one minus 2019 mean weekday occupancy, only for origin stations with at least 50 spaces
- Fare: published fare to Union per $10,000 of shed household income, reversed so a heavier burden scores low

A missing parking score is left out and the other weights are renormalized. Destination stations, where jobs in the walkshed exceed residents, do not get a parking penalty.

The quadrant split is the median of the market score and the median of the conditions score. Priority means market at or above the median and conditions below the median.

## Primary likely constraint

The reference group is the stations in the high-market, strong-conditions quadrant. For each condition, the deficit is the reference median minus the station's score. The largest deficit is the primary likely constraint. Its share is that deficit divided by the sum of the positive deficits. A second deficit within 10 points is a tie.

Land use replaces that label when the housing-growth rank is at least 67 and the walk-catchment rank is 33 or lower. The market is being carried by growth that has not yet produced a walkable station. I keep the largest numeric deficit beside that label. The share is the share of that numeric deficit. It is not a share I assign to the land-use rule.

I repeat the deficit against the median of the station's own line. If the label changes, I flag it. I do not treat that station as a firm recommendation.

## What I left out

I did not use a first-match rule, because a fixed order would call a station a parking problem whenever the 2019 lot was full, even if the bus gap was larger. I did not use feature importance or a cluster model. With about 70 stations those methods produce a label that looks more precise than the sample allows.
