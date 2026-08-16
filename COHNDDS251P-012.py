#!/usr/bin/env python
# coding: utf-8

# In[11]:


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

gdf = gdf.to_crs(3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms"
)

gdf["time_str"] = gdf["time_dt"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)

gdf["mag"] = gdf["mag"].fillna(0)

gdf["risk"] = pd.cut(
    gdf["mag"],
    [-1, 3, 5, 10],
    labels=[
        "Low Risk",
        "Medium Risk",
        "High Risk"
    ]
)

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
].dropna()


# ============================================================
# TASK 2: BOKEH + GEOPANDAS MAP
# ============================================================

source = ColumnDataSource(df)

p = figure(
    title="USGS Earthquake Interactive Geo Dashboard",
    x_axis_type="mercator",
    y_axis_type="mercator",
    width=900,
    height=600,
    tools="pan,wheel_zoom,reset,save"
)

p.add_tile(
    WMTSTileSource(
        url="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors © CARTO"
    )
)


# ============================================================
# TASK 3: HOVER TOOL
# ============================================================

points = p.scatter(
    x="x",
    y="y",
    size=8,
    marker="circle",
    source=source
)

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
# TASK 4: CHOROPLETH-STYLE COLOUR INTENSITY
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],
    low=df["mag"].min(),
    high=df["mag"].max()
)

points.glyph.fill_color = {
    "field": "mag",
    "transform": mapper
}

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


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
    step=86400000,
    width=250
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
    width=250
)


# ============================================================
# TASK 3: FILTER CALLBACK
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

    source.data = filtered


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


# In[ ]:




