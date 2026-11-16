# Data dictionary

`data/processed/station_scorecard.csv` is one row per GO or UP station. Scores run from 0 to 100. A higher score is a stronger market or a stronger condition.

| Column | Meaning |
| --- | --- |
| station_id | GO stop code |
| station_name | Name with the GO suffix removed |
| line | Primary rail line code. UP is used only where there is no GO line |
| line_name | Line name |
| weekday_departures | Trains a passenger can board on Wednesday 18 November 2026 |
| weekday_to_union | Of those, trips that reach Union later in the same trip |
| am_peak_to_union | Toward-Union boardings possible from 06:00 to 09:00 |
| midday_departures | Boardable departures from 09:30 to 15:00 |
| saturday_departures, sunday_departures | Boardable departures on 21 and 22 November 2026 |
| offpeak_weekend_departures | Midday, evening, Saturday, and Sunday departures, summed |
| feeder_am_arrivals | Local transit arrivals within 250 m, 06:00 to 09:00, on that operator's representative Wednesday |
| am_transfer_wait_min | Median scheduled minutes from those arrivals to the next train toward Union |
| main_feeder_agency | Operator with the most arrivals that day |
| parking_spaces_2019 | Spaces in the December 2019 open file, where I could match the facility |
| parking_utilization_2019 | Mean occupied spaces over the 2019 months with a non-zero count, divided by capacity |
| walk_pop, walk_jobs | 2021 residents and usual-place-of-work jobs inside the 800 m walkshed |
| walk_reach_ratio | Share of the 800 m circle that the walkshed covers |
| shed_pop, shed_jobs | Residents and jobs in the 10 km station shed |
| shed_wfh_share | Worked at home divided by employed residents, in the shed |
| commute_to_toronto_share | Share of the station municipality's commuters whose usual workplace is Toronto |
| fare_to_union | Lowest published GO fare from the station zone to Union, dollars |
| fare_burden | That fare per $10,000 of shed household income |
| role | Destination if jobs in the walkshed exceed residents, otherwise origin |
| market_score | Mean of the shed size, Toronto-commute, and recent-housing ranks |
| service_score, feeder_score, walk_score, parking_score, fare_score | Condition ranks. Parking is blank where it does not apply |
| conditions_score | Equal-weight mean of the condition scores that apply |
| quadrant | priority, market and conditions, conditions ahead of market, or market and conditions both thin |
| primary_likely | Analysis 2 label for priority stations and the Kitchener case stations |
| constraint_share | Largest deficit divided by the sum of positive deficits |
| is_tie | True when the second deficit is within 10 points of the first |
| primary_vs_corridor | The same label measured against the station's own line |
| label_changes_with_corridor | True when those two labels differ |

`data/processed/recommendations.csv` is the action table for the priority stations and the Kitchener case stations. `data/processed/feeder_service_dates.csv` records which Wednesday I used for each local operator.
