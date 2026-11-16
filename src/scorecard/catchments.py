"""Station catchments: an 800 m walkshed on the OpenStreetMap walking network, and a station shed.

The station shed is the area closer to a station than to any other GO or UP station (a Voronoi
cell), capped at 10 km. It stands in for the drive and transit access market.
"""

import geopandas as gpd
import networkx as nx
import pandas as pd
from pyrosm import OSM
from shapely.geometry import LineString, MultiPoint
from shapely.ops import unary_union
from shapely import voronoi_polygons

from . import config as C

PBF = C.RAW / "osm" / "ontario.osm.pbf"


def _line(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type == "MultiLineString":
        geom = max(geom.geoms, key=lambda part: part.length)
    return geom if geom.geom_type == "LineString" else None


def _walking_edges(stations):
    """Walking streets within 1.2 km of a station, from the Geofabrik Ontario extract.

    I use the extract rather than the public Overpass API. A single query covering every
    station was rejected when that server was at capacity, and the extract is reproducible.
    The extract does not carry from-node and to-node ids, so I connect segments later at
    every vertex.
    """
    cache = C.INTERIM / "walking_edges.parquet"
    if cache.exists():
        df = pd.read_parquet(cache)
        return gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df.geometry), crs=C.CRS_METRIC)
    b = C.STUDY_BBOX
    osm = OSM(str(PBF), bounding_box=[b["xmin"], b["ymin"], b["xmax"], b["ymax"]])
    edges = osm.get_network(network_type="walking")
    edges = edges[["length", "geometry"]].dropna(subset=["geometry"]).to_crs(C.CRS_METRIC)
    near = unary_union(stations.to_crs(C.CRS_METRIC).geometry.buffer(C.WALK_DISTANCE_M + 400))
    edges = edges[edges.intersects(near)].copy()
    edges.to_parquet(cache)
    return edges


def _key(coord):
    # One metre is enough to join coordinates that are the same intersection and
    # not enough to bridge a real gap in the street network.
    return (round(coord[0]), round(coord[1]))


def _graph_from_edges(local):
    """Connect every vertex, not only the ends of a way.

    OpenStreetMap stores a road as one line that other roads meet in the middle.
    Joining only the two ends leaves each way as its own fragment, and the walkshed
    collapses to a single street.
    """
    graph = nx.Graph()
    for geom in local.geometry:
        line = _line(geom)
        if line is None:
            continue
        coords = list(line.coords)
        for i in range(len(coords) - 1):
            a, b = _key(coords[i]), _key(coords[i + 1])
            if a == b:
                continue
            length = ((coords[i][0] - coords[i + 1][0]) ** 2 + (coords[i][1] - coords[i + 1][1]) ** 2) ** 0.5
            if graph.has_edge(a, b) and graph[a][b]["length"] <= length:
                continue
            graph.add_edge(a, b, length=length, geometry=None)
            graph[a][b]["points"] = (coords[i], coords[i + 1])
    return graph


def _origin(graph, point, snap_m=150):
    """Start the walk on the street grid, not on a short platform stub.

    The nearest walk segment at a rail station is often a disconnected platform path.
    Within 150 m, I start on the largest connected piece of the walking network.
    """
    size = {}
    for component in nx.connected_components(graph):
        n = len(component)
        for node in component:
            size[node] = n
    best = None
    nearest = None
    for node, n in size.items():
        dist = ((node[0] - point.x) ** 2 + (node[1] - point.y) ** 2) ** 0.5
        if nearest is None or dist < nearest[0]:
            nearest = (dist, node)
        if dist <= snap_m and (best is None or (-n, dist) < best[0]):
            best = ((-n, dist), node)
    return best[1] if best is not None else nearest[1]


def build_walksheds(stations):
    """Network walkshed polygon per station, plus the share of the 800 m circle it covers."""
    edges = _walking_edges(stations)
    index = edges.sindex
    pts = stations.to_crs(C.CRS_METRIC)
    rows = []
    for s in pts.itertuples():
        circle = s.geometry.buffer(C.WALK_DISTANCE_M)
        search = s.geometry.buffer(C.WALK_DISTANCE_M + 400)
        local = edges.iloc[index.query(search, predicate="intersects")]
        graph = _graph_from_edges(local)
        if graph.number_of_edges() == 0:
            rows.append({"station_id": s.station_id, "walk_reach_ratio": 0.0, "geometry": circle})
            continue
        origin = _origin(graph, s.geometry)
        lengths = nx.single_source_dijkstra_path_length(graph, origin, cutoff=C.WALK_DISTANCE_M, weight="length")
        reached = [
            LineString(data["points"])
            for a, b, data in graph.edges(data=True)
            if a in lengths and b in lengths
        ]
        if not reached:
            rows.append({"station_id": s.station_id, "walk_reach_ratio": 0.0, "geometry": s.geometry.buffer(C.WALK_EDGE_BUFFER_M)})
            continue
        shed = unary_union([line.buffer(C.WALK_EDGE_BUFFER_M) for line in reached]).intersection(circle)
        rows.append({"station_id": s.station_id, "walk_reach_ratio": float(shed.area / circle.area), "geometry": shed})
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=C.CRS_METRIC)


def build_station_sheds(stations):
    """Voronoi cell around each station, clipped to a 10 km radius."""
    pts = stations.to_crs(C.CRS_METRIC)
    hull = unary_union(pts.geometry).buffer(C.SHED_CAP_M * 2)
    cells = voronoi_polygons(MultiPoint(list(pts.geometry)), extend_to=hull)
    cells = gpd.GeoDataFrame(geometry=list(cells.geoms), crs=C.CRS_METRIC)
    joined = gpd.sjoin(pts[["station_id", "geometry"]], cells, predicate="within")
    out = []
    for r in joined.itertuples():
        cell = cells.geometry.iloc[r.index_right]
        out.append({"station_id": r.station_id, "geometry": cell.intersection(r.geometry.buffer(C.SHED_CAP_M))})
    return gpd.GeoDataFrame(out, geometry="geometry", crs=C.CRS_METRIC)


def load_census_geography():
    def read(name):
        df = pd.read_parquet(C.CENSUS_DIR / f"{name}.parquet")
        return gpd.GeoDataFrame(df, geometry=gpd.GeoSeries.from_wkb(df.geometry), crs=C.CRS_WGS84).to_crs(
            C.CRS_METRIC
        )

    return read("da_boundaries"), read("ct_boundaries"), read("csd_boundaries")


def area_weight(zones, units, value_cols, zone_id="station_id"):
    """Apportion unit totals to zones by the share of each unit's area that falls inside the zone."""
    units = units.copy()
    units["unit_area"] = units.geometry.area
    pieces = gpd.overlay(zones[[zone_id, "geometry"]], units, how="intersection", keep_geom_type=True)
    w = pieces.geometry.area / pieces.unit_area
    out = pieces[[zone_id]].copy()
    for c in value_cols:
        out[c] = pieces[c].fillna(0) * w
    return out.groupby(zone_id, as_index=False).sum()
