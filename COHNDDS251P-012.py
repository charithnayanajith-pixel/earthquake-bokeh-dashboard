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
# TASK 1: IMPORT GEOSPATIAL DATA
# ============================================================

url = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/"
    "summary/all_month.geojson"
)

gdf = gpd.read_file(url)


# ============================================================
# CONVERT TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# TIME HANDLING
# ============================================================

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms",
    errors="coerce"
)

gdf["time_str"] = gdf["time_dt"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)


# ============================================================
# MAGNITUDE
# ============================================================

gdf["mag"] = gdf["mag"].fillna(0)


# ============================================================
# RISK CLASSIFICATION
# ============================================================

gdf["risk"] = pd.cut(
    gdf["mag"],
    bins=[-1, 2.5, 4.5, 10],
    labels=[
        "Low Risk",
        "Medium Risk",
        "High Risk"
    ]
).astype(str)


# ============================================================
# PREPARE DATA
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
    subset=[
        "x",
        "y",
        "time_dt",
        "risk"
    ]
)


# ============================================================
# COLUMN DATA SOURCE
# ============================================================

source = ColumnDataSource(
    data=ColumnDataSource.from_df(df)
)


# ============================================================
# TASK 2: CREATE BOKEH MAP
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
# ADD MAP TILES
# ============================================================

p.add_tile(
    WMTSTileSource(
        url="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors © CARTO"
    )
)


# ============================================================
# TASK 4: COLOUR MAPPING
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

    size=8,

    marker="circle",

    source=source,

    fill_color={
        "field": "mag",
        "transform": mapper
    },

    fill_alpha=0.7,

    line_color="black",

    line_width=0.5
)


# ============================================================
# COLOR BAR
# ============================================================

color_bar = ColorBar(
    color_mapper=mapper,

    title="Magnitude",

    label_standoff=10
)

p.add_layout(
    color_bar,
    "right"
)


# ============================================================
# TASK 3: HOVER TOOL
# ============================================================

hover = HoverTool(
    renderers=[points],

    tooltips=[
        ("Location", "@place"),
        ("Magnitude", "@mag{0.0}"),
        ("Time", "@time_str"),
        ("Risk", "@risk")
    ]
)

p.add_tools(hover)


# ============================================================
# TASK 3: TIME SLIDER
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=df["time_dt"].min(),

    end=df["time_dt"].max(),

    value=(
        df["time_dt"].min(),
        df["time_dt"].max()
    ),

    step=24 * 60 * 60 * 1000,

    width=300
)


# ============================================================
# TASK 3: RISK FILTER
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
# FILTER CALLBACK
# ============================================================

def update(attr, old, new):

    start, end = date_slider.value

    filtered = df[
        (df["time_dt"] >= pd.to_datetime(start)) &
        (df["time_dt"] <= pd.to_datetime(end))
    ]

    if risk_filter.value != "All":

        filtered = filtered[
            filtered["risk"] == risk_filter.value
        ]

    source.data = ColumnDataSource.from_df(
        filtered
    )


# ============================================================
# CONNECT FILTERS
# ============================================================

date_slider.on_change(
    "value_throttled",
    update
)

risk_filter.on_change(
    "value",
    update
)


# ============================================================
# TASK 5: BOKEH SERVER
# ============================================================

layout = row(
    risk_filter,
    date_slider,
    p
)

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
