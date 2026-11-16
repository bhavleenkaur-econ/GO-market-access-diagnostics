-- Scheduled transfer waits, computed with an as-of join.
-- Bus to train: each local arrival is matched to the next weekday GO or UP departure toward Union
-- that leaves at least {min_transfer} seconds later.
-- Train to bus: each weekday train arrival from Union is matched to the next local departure.
-- Waits are capped at {cap} seconds so a station with no midday trains does not produce
-- an unbounded number; the cap is reported, not hidden.
CREATE OR REPLACE TABLE transfer_waits AS
WITH bus_arr AS (
    SELECT station_id, agency, route_id, arr_sec, arr_sec + {min_transfer} AS ready_sec
    FROM local_events WHERE can_alight
),
train_dep AS (
    SELECT station_id, dep_sec FROM rail_events
    WHERE day_type = 'weekday' AND can_board AND toward_union
),
b2t AS (
    SELECT b.station_id, b.agency, b.route_id, b.arr_sec AS event_sec,
           least(coalesce(t.dep_sec - b.arr_sec, {cap}), {cap}) AS wait_sec,
           'bus_to_train' AS direction
    FROM bus_arr b
    ASOF LEFT JOIN train_dep t ON b.station_id = t.station_id AND t.dep_sec >= b.ready_sec
),
train_arr AS (
    SELECT station_id, arr_sec, arr_sec + {min_transfer} AS ready_sec FROM rail_events
    WHERE day_type = 'weekday' AND can_alight AND from_union
),
bus_dep AS (
    SELECT station_id, agency, route_id, dep_sec FROM local_events WHERE can_board
),
t2b AS (
    SELECT t.station_id, b.agency, b.route_id, t.arr_sec AS event_sec,
           least(coalesce(b.dep_sec - t.arr_sec, {cap}), {cap}) AS wait_sec,
           'train_to_bus' AS direction
    FROM train_arr t
    ASOF LEFT JOIN bus_dep b ON t.station_id = b.station_id AND b.dep_sec >= t.ready_sec
)
SELECT * FROM b2t
UNION ALL
SELECT * FROM t2b;
