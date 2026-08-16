import geopandas as gpd
import pandas as pd

from bokeh.io import curdoc
from bokeh.plotting import figure
from bokeh.models import (
    ColumnDataSource,
    HoverTool,
    DateRangeSlider,
    Select,
    LinearColorMapper,
    ColorBar,
    WMTSTileSource
)
from bokeh.palettes import YlOrRd
from bokeh.layouts import row


# ============================================================
# TASK 1 - IMPORT DATA
# ============================================================

url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"

gdf = gpd.read_file(url)

gdf = gdf.to_crs(3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# DATE
# ============================================================

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms"
)

gdf["time_str"] = gdf["time_dt"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)


# ============================================================
# MAGNITUDE
# ============================================================

gdf["mag"] = gdf["mag"].fillna(0)


# ============================================================
# RISK
# ============================================================

gdf["risk"] = "Low Risk"

gdf.loc[
    gdf["mag"] >= 2.5,
    "risk"
] = "Medium Risk"

gdf.loc[
    gdf["mag"] >= 4.5,
    "risk"
] = "High Risk"


# ============================================================
# DATAFRAME
# ============================================================

df = gdf[
    [
        "x",
        "y",
        "place",
        "mag",
        "time_dt",
        "time_str",
        "risk"
    ]
].dropna(
    subset=["x", "y", "time_dt"]
)


# ============================================================
# BOKEH SOURCE
# ============================================================

source = ColumnDataSource(df)


# ============================================================
# MAP
# ============================================================

p = figure(
    title="USGS Earthquake Interactive Geo Dashboard",

    x_axis_type="mercator",
    y_axis_type="mercator",

    x_range=(-20000000, 20000000),
    y_range=(-10000000, 10000000),

    width=900,
    height=600,

    tools="pan,wheel_zoom,box_zoom,reset,save"
)


# ============================================================
# MAP TILES
# ============================================================

p.add_tile(
    WMTSTileSource(
        url="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors © CARTO"
    )
)


# ============================================================
# COLOUR MAPPER
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],
    low=df["mag"].min(),
    high=df["mag"].max()
)


# ============================================================
# EARTHQUAKE POINTS
# ============================================================

points = p.scatter(
    x="x",
    y="y",
    source=source,
    size=8,
    marker="circle",

    fill_color={
        "field": "mag",
        "transform": mapper
    },

    fill_alpha=0.8,
    line_color="black"
)


# ============================================================
# COLOR BAR
# ============================================================

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


# ============================================================
# HOVER
# ============================================================

p.add_tools(
    HoverTool(
        renderers=[points],

        tooltips=[
            ("Location", "@place"),
            ("Magnitude", "@mag{0.0}"),
            ("Time", "@time_str"),
            ("Risk", "@risk")
        ]
    )
)


# ============================================================
# TIME FILTER
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=df["time_dt"].min(),

    end=df["time_dt"].max(),

    value=(
        df["time_dt"].min(),
        df["time_dt"].max()
    ),

    step=86400000,

    width=300
)


# ============================================================
# RISK FILTER
# ============================================================

risk_filter = Select(
    title="Risk Level",

    value="All",

    options=[
        "All",
        "High Risk",
        "Medium Risk",
        "Low Risk"
    ],

    width=200
)


# ============================================================
# FILTER
# ============================================================

def update():

    filtered = df.copy()


    # Risk filter

    if risk_filter.value == "High Risk":

        filtered = filtered[
            filtered["risk"] == "High Risk"
        ]

    elif risk_filter.value == "Medium Risk":

        filtered = filtered[
            filtered["risk"] == "Medium Risk"
        ]

    elif risk_filter.value == "Low Risk":

        filtered = filtered[
            filtered["risk"] == "Low Risk"
        ]


    # Time filter

    start = pd.to_datetime(
        date_slider.value[0]
    )

    end = pd.to_datetime(
        date_slider.value[1]
    )

    filtered = filtered[
        (filtered["time_dt"] >= start) &
        (filtered["time_dt"] <= end)
    ]


    # Update source

    source.data = {
        "x": filtered["x"],
        "y": filtered["y"],
        "place": filtered["place"],
        "mag": filtered["mag"],
        "time_dt": filtered["time_dt"],
        "time_str": filtered["time_str"],
        "risk": filtered["risk"]
    }


# ============================================================
# CALLBACKS
# ============================================================

risk_filter.on_change(
    "value",
    lambda attr, old, new: update()
)

date_slider.on_change(
    "value",
    lambda attr, old, new: update()
)


# ============================================================
# LAYOUT
# ============================================================

layout = row(
    risk_filter,
    date_slider,
    p
)


# ============================================================
# BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
