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
| am_headway_min | Median minutes between consecutive weekday departures toward Union, 06:00 to 09:00. Filled with 180 when the band has fewer than two trains |
| am_max_gap_min | Longest such AM-peak gap, minutes |
| midday_headway_min | Median minutes between consecutive boardable departures, 09:30 to 15:00. Filled with 330 when the band has fewer than two trains |
| midday_max_gap_min | Longest midday gap, minutes. This is the gap that enters the service score |
| weekday_headway_min, weekday_max_gap_min | Same measures across the whole weekday toward Union, overnight excluded |
| span_hours | Weekday last departure minus first departure, in hours |
| first_departure_clock, last_departure_clock | Those two times, quoted in the brief and not scored on their own |
| saturday_span_hours, sunday_span_hours | Span on 21 and 22 November 2026. A day with one train has a span of zero |
| weekend_span_hours | Mean of the Saturday and Sunday spans, with a missing day as zero |
| ivt_to_union_min | Median scheduled minutes from departure at the station to arrival at Union |
| offpeak_weekend_departures | Midday, evening, Saturday, and Sunday departures, summed. Evidence only. It does not enter the service score |
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
| fare_to_union_high | Highest published fare for the same zone pair. On this feed it equals the lowest, because there is one product |
| fare_product_n | Number of fare products from the station zone to Union zone 02 |
| sticker_burden | The published fare per $10,000 of shed household income. Kept beside the score. It does not enter it |
| generalized_cost | Published fare plus the value of in-vehicle time and of half the AM headway, at half the shed wage |
| fare_burden | That generalized cost per $10,000 of shed household income. This is what the fare score ranks |
| role | Destination if jobs in the walkshed exceed residents, otherwise origin |
| market_score | Mean of the shed size, Toronto-commute, and recent-housing ranks |
| service_score, feeder_score, walk_score, parking_score, fare_score | Condition ranks. Parking is blank where it does not apply |
| conditions_score | Equal-weight mean of the condition scores that apply |
| quadrant | priority, market and conditions, conditions ahead of market, or market and conditions both thin |
| conditions_gap | Conditions median minus the station's conditions score. Positive means the station is on the priority side of the cut |
| near_cut | True when the market score or the conditions score is within 5 points of its median |
| threshold_class | clear, threshold-sensitive, looser cut only, or not priority. Clear means high market and conditions below the 40th percentile |
| primary_likely | Analysis 2 label for priority stations and the Kitchener case stations |
| numeric_primary | The largest score deficit, before a land-use rule replaces the published label |
| runner_up | The second-largest numeric deficit, whether or not it is close enough to call a tie |
| constraint_share | Largest deficit divided by the sum of positive deficits |
| is_tie | True when the second deficit is within 10 points of the first |
| confidence | high, medium, or low, from the share, the tie, the corridor check, the near-cut flag, and any land-use override |
| supporting_evidence | The numbers behind the primary label |
| contradictory_evidence | The condition with the smallest deficit, which is the station's strongest condition relative to the reference group |
| primary_vs_corridor | The same label measured against the station's own line |
| label_changes_with_corridor | True when those two labels differ |

`reports/evidence.csv` is the competing-evidence table for the priority stations and the Kitchener case stations.

`data/processed/recommendations.csv` is the action table for the priority stations and the Kitchener case stations. `data/processed/feeder_service_dates.csv` records which Wednesday I used for each local operator.
