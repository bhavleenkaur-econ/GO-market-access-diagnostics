# Where GO ridership cannot show up yet

## The question

I asked which GO and UP stations have a strong surrounding travel market, but weak walk access, local connections, rail service, parking headroom, or fare. I did not ask which stations have low ridership. Station boardings and PRESTO transactions are not open, so a ridership model would have been a guess. The scorecard is the evidence I can defend, and it is the question I would take to Transit Strategy and Insights.

## What I did, in order

I first took the current GO and UP Express schedules and counted trains on Wednesday 2026-11-18, the Saturday, and the Sunday inside that feed. I then placed every local bus stop within 250 m of a station, using the latest open feed from each of 14 municipal operators, and measured the scheduled wait from an arriving bus to the next train toward Union. I then built two catchments. The walk catchment is the street network within 800 m. The station shed is the area closer to that station than to any other, capped at 10 km. I put 2021 Census population, jobs, recent housing, work from home, and the share of commuters whose usual workplace is Toronto into those catchments. I used the published GO fare to Union and the 2019 parking file as the fare and parking conditions. Only after that table was complete did I score the stations and name a primary likely constraint.

## The two analyses

Analysis 1 is a quadrant, not a cause. I scored 70 stations. Union Station is the network destination, and Stratford is outside the tracted census area, so I left both out of the ranking. The median market score is 50.7 and the median conditions score is 48.1. A station above the market median and below the conditions median is a priority: the market is ahead of the conditions.

Analysis 2 names the primary likely constraint for those priority stations. I compared each condition with the 21 stations that have both a strong market and strong conditions. The deficit is the number of points the station sits below that reference median. The largest deficit is the primary likely constraint. If the second deficit is within 10 points, I call it a tie and I do not recommend a single capital project. Land use is the label when recent housing growth carries the market score while the walk catchment is still thin.

## What I found

I found 14 priority stations: 4 land use, 4 rail service, 2 walk access, 2 fare burden, 1 local connections, 1 parking headroom.

The share is the largest numeric deficit divided by the sum of the deficits that are below the reference stations. Where I use the land-use rule, that share still belongs to the largest numeric deficit. I do not treat the land-use label as a percentage.

| Station | Line | Market | Conditions | What I would act on | Largest deficit | Close second | On its own line |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| Oriole | Richmond Hill | 86 | 28 | Land use | Rail service (31%) |  | Parking headroom |
| Etobicoke North | Kitchener | 67 | 45 | Walk access | Walk access (55%) |  | Walk access |
| Unionville | Stouffville | 64 | 35 | Land use | Walk access (30%) |  | Walk access |
| Langstaff | Richmond Hill | 63 | 37 | Rail service | Rail service (43%) |  | Fare burden |
| Milton | Milton | 62 | 40 | Rail service | Rail service (33%) | Fare burden | Parking headroom |
| Maple | Barrie | 62 | 48 | Local connections | Local connections (37%) |  | Parking headroom |
| Markham | Stouffville | 61 | 45 | Parking headroom | Parking headroom (39%) | Local connections | Parking headroom |
| Old Cummer | Richmond Hill | 60 | 41 | Rail service | Rail service (47%) |  | Local connections |
| Milliken | Stouffville | 60 | 40 | Fare burden | Fare burden (34%) | Parking headroom | Parking headroom |
| Kitchener | Kitchener | 58 | 43 | Fare burden | Fare burden (50%) |  | Fare burden |
| Richmond Hill | Richmond Hill | 57 | 45 | Rail service | Rail service (52%) |  | Parking headroom |
| Durham College Oshawa | Lakeshore East | 55 | 38 | Walk access | Walk access (46%) | Fare burden | Walk access |
| Bloomington | Richmond Hill | 53 | 20 | Land use | Rail service (34%) |  | Walk access |
| Gormley | Richmond Hill | 52 | 33 | Land use | Rail service (33%) |  | Walk access |

**Rail service.** Langstaff, Milton, Old Cummer, and Richmond Hill. Add off-peak and weekend rail trips before adding more peak trains. The market is already there, and the timetable is the thin condition. The owner is Metrolinx service planning.

The second deficit is within 10 points at Milton (fare burden), so I would not fund only one of them.

Compared with its own line, the largest deficit changes at Langstaff (fare burden), Milton (parking headroom), Old Cummer (local connections), Richmond Hill (parking headroom).

Langstaff, Old Cummer, and Richmond Hill are all on the Richmond Hill line. I first compared them with the rest of the network, where the timetable is the gap. I then compared them with each other. Stations that share one timetable have the same service score, so the own-line deficit moves to another condition. I would keep the service recommendation, because the within-line comparison cannot see a gap that the whole line shares.

**Local connections.** Maple. Add AM-peak bus arrivals and shorten the scheduled wait to the train, with the municipal operator that already serves the station. The owner is York Region Transit, with Metrolinx.

Maple has 9 AM-peak bus arrivals and a median wait of 18 minutes. The longest median wait in the priority set is Richmond Hill, at 28 minutes. I already flag that station for rail service, because the thin timetable is the larger gap.

Compared with its own line, the largest deficit changes at Maple (parking headroom).

**Walk access.** Etobicoke North and Durham College Oshawa. Treat walk access as the constraint. More trains will not reach people who cannot get to the platform on foot. The owner is Metrolinx station access, with the municipality.

The second deficit is within 10 points at Durham College Oshawa (fare burden), so I would not fund only one of them.

**Parking headroom.** Markham. The 2019 lot was already full on a normal weekday. Do not plan peak ridership growth on more parking spaces until occupancy is measured again. The owner is Metrolinx station access.

The second deficit is within 10 points at Markham (local connections), so I would not fund only one of them.

**Fare burden.** Milliken and Kitchener. The fare to Union is high relative to household income around the station. Review the fare product before adding service that those households may not buy. The owner is Metrolinx fare policy.

The second deficit is within 10 points at Milliken (parking headroom), so I would not fund only one of them.

Compared with its own line, the largest deficit changes at Milliken (parking headroom).

**Land use.** Oriole, Unionville, Bloomington, and Gormley. Current population and jobs inside the walk are thin, and the market score is carried by recent housing growth. I would treat this as a land-use question, not as a near-term service add. The owner is Municipal planning.

Gormley and Bloomington also have no local bus stop within 250 m. A rail add at those stations would still leave the trip dependent on driving or a long walk.

Compared with its own line, the largest deficit changes at Oriole (parking headroom), Bloomington (walk access), Gormley (walk access).

I then recomputed the conditions score with access weighted twice as heavily, and again with service weighted twice as heavily. Rank correlation with the equal-weight score is equal vs access heavy 0.97, equal vs service heavy 0.97, access heavy vs service heavy 0.92. Stations that stay in the priority set under all three weights are: Bloomington, Etobicoke North, Gormley, Langstaff, Milliken, Milton, Markham, Old Cummer, Oriole, Durham College Oshawa, Richmond Hill, Unionville. Stations that leave the priority set when I weight access more heavily are: Kitchener. Stations that join when I weight service more heavily are: Guelph Central, Streetsville.

## Kitchener line

I then looked at the Kitchener line on its own, because this is the corridor I can speak to from Guelph. Acton: 5 AM peak trips toward Union, 3 midday departures, 4 Saturday departures. Guelph Central: 6 AM peak trips toward Union, 4 midday departures, 6 Saturday departures. Kitchener: 6 AM peak trips toward Union, 5 midday departures, 6 Saturday departures. Georgetown: 7 AM peak trips toward Union, 3 midday departures, 4 Saturday departures. Mount Pleasant: 6 AM peak trips toward Union, 12 midday departures, 34 Saturday departures. Brampton Innovation District: 6 AM peak trips toward Union, 11 midday departures, 34 Saturday departures. Bramalea: 11 AM peak trips toward Union, 23 midday departures, 52 Saturday departures.

Guelph Central is the station I can check on the ground. Its market score is 51 and its conditions score is 49.2. The conditions median is 48.1, so Guelph sits just on the strong-conditions side of the split and I leave it out of the priority set. The largest deficit against the reference stations is still fare burden, at 61 points. The walk catchment has about 4,489 residents and 3,561 jobs, and the station shed has about 150,996 residents. The census subdivision sends 1.7% of its commuters to Toronto, and 26% of employed residents in the shed worked at home in 2021. The 2019 lot has 18 spaces. That is too small to score as a network commuter lot, and it was over capacity in 2019. Local buses are Guelph Transit's. The AM-peak scheduled wait from a bus to the next train toward Union is 19 minutes.

Kitchener is in the priority set. The fare to Union is $19.40, against a walk catchment of about 4,491 residents and 2,287 jobs, so the thin condition is the fare, not the walk. When I weight access more heavily, Kitchener leaves the priority set, because the walk catchment is already strong and the gap is the fare. When I weight service more heavily, Kitchener stays in the priority set. Under that same service weighting, Guelph Central joins the priority set.

Etobicoke North is the Kitchener station I would act on for walk access. The walkshed covers 14% of the 800 m circle and holds about 1 resident and 330 jobs. The station sits in employment land, with a station shed of about 162,309 residents and 79% of the home municipality's commuters working in Toronto.

## What I would measure next

If a local connection is shortened, I would track the scheduled AM-peak wait and, once boardings exist, boardings at that station against another station on the same line. If span of service is added, I would track off-peak and weekend boardings. I would not read a change as the effect of the intervention without accounting for return to office, construction, and the April 2024 service increase, which added trips on Lakeshore West, Lakeshore East, Kitchener, Stouffville, and Milton. That increase is an evaluation design, not a result I can estimate from open data.

## What this does not say

A weak score is a weak condition, not a low ridership number. The 2021 Census counts commuting during a period of high work from home, and I use that as a feature of the market rather than correcting it away. Parking is a 2019 snapshot. Transfer waits are scheduled, not observed. Catchments and municipal commute shares are approximations. Service and parking were supplied with ridership in mind, so I do not treat a score as a causal effect.

