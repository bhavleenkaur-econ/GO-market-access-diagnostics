"""Figures and the station map. Every number on a figure comes from the scored table."""

import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from . import config as C

plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 140})

QUADRANT_ORDER = [
    "priority",
    "market and conditions",
    "conditions ahead of market",
    "market and conditions both thin",
]


def _save(fig, name):
    C.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(C.FIGURES / name, bbox_inches="tight")
    plt.close(fig)


def quadrant(scored):
    df = scored[scored["in_score"]].copy()
    fig, ax = plt.subplots(figsize=(11.6, 7.4))
    colors = {
        "priority": "#b45309",
        "market and conditions": "#1f6f5b",
        "conditions ahead of market": "#3b6ea5",
        "market and conditions both thin": "#8a8175",
    }
    legend_names = {
        "priority": "Priority",
        "market and conditions": "Market and conditions",
        "conditions ahead of market": "Conditions ahead of market",
        "market and conditions both thin": "Market and conditions both thin",
    }
    draw_order = [
        "market and conditions both thin",
        "conditions ahead of market",
        "market and conditions",
        "priority",
    ]
    for name in draw_order:
        group = df[df.quadrant.eq(name)]
        ax.scatter(
            group.market_score,
            group.conditions_score,
            s=64 if name == "priority" else 28,
            c=colors[name],
            label=legend_names[name],
            zorder=4 if name == "priority" else 3,
            linewidths=0,
        )
    ax.axvline(scored.attrs["market_median"], color="#b7b1a8", lw=0.7, zorder=1)
    ax.axhline(scored.attrs["conditions_median"], color="#b7b1a8", lw=0.7, zorder=1)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Market score, 0 to 100")
    ax.set_ylabel("Enabling-conditions score, 0 to 100")
    ax.set_title("Where the market is ahead of the conditions")
    # Names sit just to the right of the axes, packed into the same vertical band as the
    # priority stations. Spreading them over the full height sent the lines through the
    # upper quadrants.
    priority = df[df.quadrant.eq("priority")].sort_values(["conditions_score", "market_score"])
    label_box = {"boxstyle": "square,pad=0.12", "facecolor": "white", "edgecolor": "none", "alpha": 0.94}
    n = len(priority)
    gap = 3.15
    top = min(54, float(priority.conditions_score.max()) + 4)
    label_ys = [top - gap * (n - 1 - i) for i in range(n)]
    for y_label, r in zip(label_ys, priority.itertuples()):
        ann = ax.annotate(
            r.station_name,
            xy=(r.market_score, r.conditions_score),
            xytext=(103, y_label),
            textcoords="data",
            fontsize=8,
            color="#7c3a12",
            va="center",
            ha="left",
            arrowprops={"arrowstyle": "-", "color": "#c4a484", "lw": 0.6, "shrinkA": 0, "shrinkB": 0},
            bbox=label_box,
            annotation_clip=False,
            zorder=6,
        )
        ann.set_clip_on(False)
    ax.legend(
        frameon=False,
        fontsize=9,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=2,
    )
    fig.subplots_adjust(right=0.74, bottom=0.18)
    _save(fig, "quadrant.png")


def deficits(scored):
    df = scored[scored.quadrant.eq("priority")].sort_values("market_score", ascending=False)
    if df.empty:
        return
    cols = [f"deficit_{c}" for c in C.CONDITIONS]
    show = df.set_index("station_name")[cols].rename(columns=lambda c: C.CONDITION_LABELS[c.replace("deficit_", "")])
    palette = ["#1f4e79", "#c47b2b", "#1f6f5b", "#9b2335", "#6b3fa0"]
    fig, ax = plt.subplots(figsize=(10.4, 7.6))
    show.plot.barh(ax=ax, width=0.84, color=palette, legend=False, zorder=3)
    ax.axvline(0, color="#444", lw=0.6, zorder=2)
    ax.grid(axis="x", color="#ece7df", lw=0.6, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel("Points below the reference stations")
    ax.set_ylabel("")
    ax.set_title("How far each priority station sits below the reference stations")
    ax.legend(
        handles=[Patch(facecolor=color, label=name) for color, name in zip(palette, show.columns)],
        frameon=False,
        fontsize=9,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.14),
        ncol=3,
    )
    ax.invert_yaxis()
    fig.subplots_adjust(bottom=0.2, left=0.24)
    _save(fig, "deficits.png")


def kitchener(scored):
    df = scored[scored.station_id.isin(C.KITCHENER_CASE)].sort_values("weekday_to_union")
    fig, ax = plt.subplots(figsize=(8, 4.4))
    x = range(len(df))
    ax.bar([i - 0.18 for i in x], df.am_peak_to_union, width=0.36, label="AM peak trips toward Union", color="#1f4e79")
    ax.bar([i + 0.18 for i in x], df.midday_departures, width=0.36, label="Midday departures", color="#c47b2b")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df.station_name, rotation=20, ha="right")
    ax.set_ylabel("Scheduled trains, Wednesday 18 Nov 2026")
    ax.set_title("Kitchener line: peak trips and midday trips")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, "kitchener_service.png")


def station_map(scored, walks):
    import folium

    points = gpd.GeoDataFrame(scored, geometry=gpd.points_from_xy(scored.lon, scored.lat), crs="EPSG:4326")
    centre = [points.lat.mean(), points.lon.mean()]
    fmap = folium.Map(location=centre, zoom_start=9, tiles="OpenStreetMap")
    colors = {
        "Rail service": "#1f4e79",
        "Local connections": "#b45309",
        "Walk access": "#1f6f5b",
        "Parking headroom": "#6b3fa0",
        "Fare burden": "#9b2335",
        "Land use": "#5c5346",
    }
    label = scored.set_index("station_id")["primary_likely"].map(
        lambda k: C.CONDITION_LABELS.get(k, "Land use" if k == "land_use" else "Not a priority station")
    )
    for r in points.itertuples():
        name = label.get(r.station_id, "Not a priority station")
        color = colors.get(name, "#8a8175")
        if r.quadrant != "priority":
            color = "#8a8175"
        folium.CircleMarker(
            [r.lat, r.lon],
            radius=7 if r.quadrant == "priority" else 4,
            color=color,
            fill=True,
            fill_opacity=0.9,
            tooltip=f"{r.station_name}: {r.quadrant}",
            popup=folium.Popup(
                f"<b>{r.station_name}</b><br>{r.line_name}<br>Market {r.market_score:.0f}, conditions {r.conditions_score:.0f}"
                if pd.notna(r.market_score) else r.station_name,
                max_width=280,
            ),
        ).add_to(fmap)
    legend = "<div style='position:fixed;bottom:12px;left:12px;z-index:9999;background:white;padding:8px 10px;font:12px sans-serif;line-height:1.4'>"
    legend += "<b>Priority stations</b><br>" + "".join(
        f"<span style='color:{c}'>&#9679;</span> {n}<br>" for n, c in colors.items()
    )
    legend += "<span style='color:#8a8175'>&#9679;</span> Not in the priority set</div>"
    fmap.get_root().html.add_child(folium.Element(legend))
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    fmap.save(str(C.REPORTS / "station_map.html"))


def all_figures(scored, walks):
    quadrant(scored)
    deficits(scored)
    kitchener(scored)
    station_map(scored, walks)
    return [
        Line2D([0], [0], marker="o", color="#b45309", lw=0, label="priority"),
    ]
