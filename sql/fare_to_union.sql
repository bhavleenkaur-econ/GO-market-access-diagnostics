-- Published GO fare from each rail station's fare zone to Union (zone 02), from the GO GTFS fare tables.
WITH zones AS (
    SELECT stop_id AS station_id, zone_id FROM go.stops WHERE zone_id IS NOT NULL
)
SELECT z.station_id, z.zone_id,
       min(fa.price::DOUBLE) AS fare_to_union,
       max(fa.price::DOUBLE) AS fare_to_union_high,
       count(*) AS fare_product_n
FROM zones z
JOIN go.fare_rules fr ON fr.origin_id = z.zone_id AND fr.destination_id = '02'
JOIN go.fare_attributes fa ON fa.fare_id = fr.fare_id
GROUP BY ALL;
