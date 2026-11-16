-- Rail service supply per station. Departures count trains a customer can board.
SELECT station_id,
    count(*) FILTER (WHERE day_type = 'weekday' AND can_board) AS weekday_departures,
    count(*) FILTER (WHERE day_type = 'weekday' AND can_board AND toward_union) AS weekday_to_union,
    count(*) FILTER (WHERE day_type = 'weekday' AND can_board AND toward_union
                     AND dep_sec BETWEEN {am0} AND {am1}) AS am_peak_to_union,
    count(*) FILTER (WHERE day_type = 'weekday' AND can_board
                     AND dep_sec BETWEEN {md0} AND {md1}) AS midday_departures,
    count(*) FILTER (WHERE day_type = 'weekday' AND can_board
                     AND dep_sec >= {ev0}) AS evening_departures,
    count(*) FILTER (WHERE day_type = 'saturday' AND can_board) AS saturday_departures,
    count(*) FILTER (WHERE day_type = 'sunday' AND can_board) AS sunday_departures,
    min(dep_sec) FILTER (WHERE day_type = 'weekday' AND can_board) AS first_departure_sec,
    max(dep_sec) FILTER (WHERE day_type = 'weekday' AND can_board) AS last_departure_sec,
    string_agg(DISTINCT line, ',' ORDER BY line) AS lines
FROM rail_events
GROUP BY station_id
ORDER BY station_id;
