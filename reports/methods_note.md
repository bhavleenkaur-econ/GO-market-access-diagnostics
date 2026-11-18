# Methods note

I wrote this so a reader can rerun the scorecard and see where each judgement comes from. The code is in `src/scorecard/`, and the SQL is in `sql/`. Settings, weights, and thresholds are in `src/scorecard/config.py`.

## Objective

I wanted to know where a GO or UP station has a travel market that the current access and service conditions are not set up to serve. I did not estimate ridership. Open data does not include station boardings or PRESTO, and I would rather say that than fit a model to a 2019 PDF.

## Order of work

1. I downloaded GO and UP Express GTFS, 14 local GTFS feeds, the December 2019 parking file, census geography and profile values, commuting flows, jobs by place of work, and the Geofabrik Ontario OpenStreetMap extract.
2. I measured headway, the longest gap, span, and scheduled time to Union in DuckDB for one Wednesday, one Saturday, and one Sunday in the current GO feed.
3. I counted local-bus arrivals within 250 m and the scheduled wait to the next train toward Union.
4. I built an 800 m walkshed on the walking network, and a 10 km station shed.
5. I apportioned census counts into those catchments by area.
6. I scored market and conditions, split stations at the median, and then measured which condition sits furthest below the stations that are not held back.

## Service

GO publishes service by calendar date, not by a weekly calendar. I used Wednesday 18 November 2026, Saturday 21 November 2026, and Sunday 22 November 2026. All three dates are marked as service in the feed. A departure is a stop event where the passenger can board. A trip toward Union reaches Union later on the same trip.

I score timetable quality, not trip counts. Trip counts stay in the station table as evidence. For weekday departures toward Union I measure:

- the median gap between consecutive boardable departures in the AM peak, 06:00 to 09:00
- the longest such gap in the midday, 09:30 to 15:00
- the weekday span, last departure minus first departure
- the weekend span, the mean of the Saturday span and the Sunday span, with a missing day counted as zero

A gap counts in a band only when both ends fall inside the band, so the overnight does not become a headway. The first train of the day has no previous train. If a band has fewer than two departures, I fill the headway and the longest gap with the length of the band, 180 minutes in the peak and 330 minutes at midday. A single train then ranks as infrequent, rather than as a missing value. First and last departure are stored as clock times. I quote them. I do not score them separately, because they are the two ends of the span.

Scheduled in-vehicle time is the median of Union arrival minus the station departure, on weekday trips toward Union. It is a travel time, so it goes into the generalized cost, not into the service score.

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

- Rail service: AM-peak headway toward Union, reversed, the longest midday gap, reversed, weekday span, and weekend span
- Local connections: AM-peak bus arrivals, and the median AM-peak scheduled wait, reversed so a long wait scores low
- Walk access: people plus jobs in the walkshed, and walk reach
- Parking headroom: one minus 2019 mean weekday occupancy, only for origin stations with at least 50 spaces
- Fare: generalized cost of a scheduled trip to Union per $10,000 of shed household income, reversed so a heavier cost scores low

The generalized cost is the published fare plus a value of time times in-vehicle minutes plus frequency delay. The value of time is half the shed median household income, spread over 2,080 hours, then converted to dollars per minute. Frequency delay is half the AM-peak headway, the wait if the passenger does not time the arrival. I leave walk time and the bus-to-train wait out of this sum. Those minutes already sit in the walk score and the feeder score.

The GO fare file has one price for each zone pair. I do not invent a PRESTO discount. I rerun the fare deficit after subtracting $1 from every fare, after a 10% reduction, with the frequency delay at a quarter of the headway, and with the value of time at 35% and at 70% of the shed wage. I report the stations whose largest deficit changes.

A missing parking score is left out and the other weights are renormalized. Destination stations, where jobs in the walkshed exceed residents, do not get a parking penalty.

The quadrant split is the median of the market score and the median of the conditions score. Priority means market at or above the median and conditions below the median. I also record how many points the conditions score sits below that median. A station within 5 points of either median is near the cut. I recompute priority membership at the 40th and the 60th percentile of the conditions score, holding the market cut at the median. A station below the 40th is also below the median and below the 60th, so that station is in the priority set at all three cuts. A station that is priority at the median and not at the 40th is threshold-sensitive. A station that would join only at the 60th is named separately.

## Primary likely constraint

The reference group is the stations in the high-market, strong-conditions quadrant. For each condition, the deficit is the reference median minus the station's score. The largest deficit is the primary likely constraint. Its share is that deficit divided by the sum of the positive deficits. A second deficit within 10 points is a tie.

Land use replaces that label when the housing-growth rank is at least 67 and the walk-catchment rank is 33 or lower. The market is being carried by growth that has not yet produced a walkable station. I keep the largest numeric deficit beside that label. The share is the share of that numeric deficit. It is not a share I assign to the land-use rule.

I repeat the deficit against the median of the station's own line. If the label changes, I flag it. I do not treat that station as a firm recommendation.

For each priority station, and for the Kitchener case stations, I write one evidence row. It carries the primary label, the second-largest numeric deficit even when that deficit is not a tie, the raw numbers behind the label, the condition with the smallest deficit, and a confidence:

- High, when the largest deficit is at least half of the positive gaps, it is not a tie, the corridor label agrees, the station is not near the cut, and land use did not replace the numeric deficit.
- Low, when land use replaced a larger numeric deficit, or the largest deficit is under 35% of the positive gaps.
- Medium otherwise, including a tie, a corridor disagreement, or a station near the cut.

The second-largest deficit is always recorded. The tie flag still requires the two deficits to sit within 10 points.

## What I left out

I did not use a first-match rule, because a fixed order would call a station a parking problem whenever the 2019 lot was full, even if the bus gap was larger. I did not use feature importance or a cluster model. With about 70 stations those methods produce a label that looks more precise than the sample allows.
