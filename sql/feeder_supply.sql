-- Local transit supply at each GO station: arrivals in the weekday AM peak, all-day arrivals and
-- the number of distinct routes, with the agency that runs the most arrivals.
WITH by_agency AS (
    SELECT station_id, agency,
           count(*) FILTER (WHERE can_alight AND arr_sec BETWEEN {am0} AND {am1}) AS am_arrivals,
           count(*) FILTER (WHERE can_alight) AS day_arrivals,
           count(DISTINCT route_id) AS routes
    FROM local_events
    GROUP BY ALL
)
SELECT station_id,
       sum(am_arrivals) AS feeder_am_arrivals,
       sum(day_arrivals) AS feeder_day_arrivals,
       sum(routes) AS feeder_routes,
       arg_max(agency, day_arrivals) AS main_feeder_agency,
       string_agg(agency, ',' ORDER BY day_arrivals DESC) AS feeder_agencies
FROM by_agency
GROUP BY station_id;
