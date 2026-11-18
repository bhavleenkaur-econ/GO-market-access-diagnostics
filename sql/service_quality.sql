-- Timetable quality for each station.
-- Headways are gaps between consecutive weekday departures toward Union.
-- The overnight does not enter, because the first departure of the day has no previous train.
-- A gap counts in a time band only when both ends of the gap fall inside that band.

WITH toward AS (
    SELECT station_id, dep_sec,
           lag(dep_sec) OVER (PARTITION BY station_id ORDER BY dep_sec) AS prev_sec
    FROM rail_events
    WHERE day_type = 'weekday' AND can_board AND toward_union
),
gaps AS (
    SELECT station_id, dep_sec, prev_sec, dep_sec - prev_sec AS gap_sec
    FROM toward
    WHERE prev_sec IS NOT NULL
),
am AS (
    SELECT station_id,
           median(gap_sec) / 60.0 AS am_headway_min,
           max(gap_sec) / 60.0 AS am_max_gap_min,
           count(*) AS am_gap_n
    FROM gaps
    WHERE dep_sec BETWEEN {am0} AND {am1}
      AND prev_sec BETWEEN {am0} AND {am1}
    GROUP BY station_id
),
midday AS (
    SELECT station_id,
           median(gap_sec) / 60.0 AS midday_headway_min,
           max(gap_sec) / 60.0 AS midday_max_gap_min,
           count(*) AS midday_gap_n
    FROM gaps
    WHERE dep_sec BETWEEN {md0} AND {md1}
      AND prev_sec BETWEEN {md0} AND {md1}
    GROUP BY station_id
),
all_day AS (
    SELECT station_id,
           median(gap_sec) / 60.0 AS weekday_headway_min,
           max(gap_sec) / 60.0 AS weekday_max_gap_min
    FROM gaps
    GROUP BY station_id
),
day_span AS (
    SELECT station_id, day_type,
           (max(dep_sec) - min(dep_sec)) / 3600.0 AS span_hours
    FROM rail_events
    WHERE can_board AND day_type IN ('saturday', 'sunday')
    GROUP BY station_id, day_type
),
weekend AS (
    SELECT station_id,
           max(CASE WHEN day_type = 'saturday' THEN span_hours END) AS saturday_span_hours,
           max(CASE WHEN day_type = 'sunday' THEN span_hours END) AS sunday_span_hours
    FROM day_span
    GROUP BY station_id
),
ivt AS (
    SELECT e.station_id,
           median(u.arr_sec - e.dep_sec) / 60.0 AS ivt_to_union_min
    FROM rail_events e
    JOIN rail_events u
      ON u.operator = e.operator
     AND u.trip_id = e.trip_id
     AND u.station_id = 'UN'
     AND u.day_type = e.day_type
    WHERE e.day_type = 'weekday'
      AND e.can_board
      AND e.toward_union
      AND u.arr_sec >= e.dep_sec
    GROUP BY e.station_id
),
stations AS (
    SELECT DISTINCT station_id FROM rail_events
)
SELECT s.station_id,
       am.am_headway_min,
       am.am_max_gap_min,
       am.am_gap_n,
       midday.midday_headway_min,
       midday.midday_max_gap_min,
       midday.midday_gap_n,
       all_day.weekday_headway_min,
       all_day.weekday_max_gap_min,
       weekend.saturday_span_hours,
       weekend.sunday_span_hours,
       ivt.ivt_to_union_min
FROM stations s
LEFT JOIN am USING (station_id)
LEFT JOIN midday USING (station_id)
LEFT JOIN all_day USING (station_id)
LEFT JOIN weekend USING (station_id)
LEFT JOIN ivt USING (station_id);
