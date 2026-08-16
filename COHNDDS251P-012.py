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

url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"

gdf = gpd.read_file(url)


# ============================================================
# CONVERT TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# DATE AND TIME
# ============================================================

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms",
    errors="coerce"
)

# Remove timezone
gdf["time_dt"] = gdf["time_dt"].dt.tz_localize(None)

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
        "time_dt"
    ]
)


# ============================================================
# TASK 2: BOKEH DATA SOURCE
# ============================================================

source = ColumnDataSource(df)


# ============================================================
# CREATE MAP
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
# MAP TILE
# ============================================================

p.add_tile(
    WMTSTileSource(
        url="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors © CARTO"
    )
)


# ============================================================
# TASK 4: MAGNITUDE COLOUR
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
# TASK 3: HOVER TOOL
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
# TASK 3: TIME FILTER
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
# TASK 3: FILTER CALLBACK
# ============================================================

def update(attr, old, new):

    # Start with all data
    filtered = df.copy()


    # --------------------------------------------------------
    # RISK FILTER
    # --------------------------------------------------------

    if risk_filter.value != "All":

        filtered = filtered[
            filtered["risk"] == risk_filter.value
        ]


    # --------------------------------------------------------
    # TIME FILTER
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # UPDATE MAP
    # --------------------------------------------------------

    source.data = ColumnDataSource.from_df(
        filtered
    )


# ============================================================
# CONNECT RISK FILTER
# ============================================================

risk_filter.on_change(
    "value",
    update
)


# ============================================================
# CONNECT TIME FILTER
# ============================================================

date_slider.on_change(
    "value_throttled",
    update
)


# ============================================================
# TASK 5: DASHBOARD LAYOUT
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
