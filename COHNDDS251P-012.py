#!/usr/bin/env python
# coding: utf-8

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
    WMTSTileSource,
    Div,
    CustomJS
)

from bokeh.palettes import YlOrRd
from bokeh.layouts import row, column


# ============================================================
# TASK 1
# IMPORT USGS EARTHQUAKE DATA
# ============================================================

url = (
    "https://earthquake.usgs.gov/earthquakes/"
    "feed/v1.0/summary/all_month.geojson"
)

gdf = gpd.read_file(url)


# ============================================================
# TASK 2
# CONVERT GEOMETRY TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# TASK 3
# CONVERT EARTHQUAKE TIME
# ============================================================

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms",
    errors="coerce",
    utc=True
)

gdf["time_str"] = gdf["time_dt"].dt.strftime(
    "%Y-%m-%d %H:%M:%S UTC"
)


# ============================================================
# TASK 4
# MAGNITUDE
# ============================================================

gdf["mag"] = pd.to_numeric(
    gdf["mag"],
    errors="coerce"
)

gdf["mag"] = gdf["mag"].fillna(0)


# ============================================================
# TASK 5
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
# TASK 6
# SELECT REQUIRED COLUMNS
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
).reset_index(drop=True)


# ============================================================
# TASK 7
# CREATE NUMERIC TIME COLUMN
#
# IMPORTANT:
# Bokeh DateRangeSlider internally uses milliseconds.
# We therefore create one consistent millisecond column.
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 1_000_000
).astype("int64")


# ============================================================
# TASK 8
# GET MINIMUM AND MAXIMUM DATES
# ============================================================

min_time = int(df["time_ms"].min())
max_time = int(df["time_ms"].max())


# ============================================================
# TASK 9
# CREATE COMPLETE DATA SOURCE
# ============================================================

full_source = ColumnDataSource(
    data={
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "place": df["place"].tolist(),
        "mag": df["mag"].tolist(),
        "time_str": df["time_str"].tolist(),
        "risk": df["risk"].tolist(),
        "time_ms": df["time_ms"].tolist()
    }
)


# ============================================================
# TASK 10
# CREATE DISPLAY DATA SOURCE
# ============================================================

source = ColumnDataSource(
    data={
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "place": df["place"].tolist(),
        "mag": df["mag"].tolist(),
        "time_str": df["time_str"].tolist(),
        "risk": df["risk"].tolist(),
        "time_ms": df["time_ms"].tolist()
    }
)


# ============================================================
# TASK 11
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

    tools=[
        "pan",
        "wheel_zoom",
        "box_zoom",
        "reset",
        "save"
    ]
)


# ============================================================
# TASK 12
# ADD CARTO BASEMAP
# ============================================================

p.add_tile(
    WMTSTileSource(
        url=(
            "https://a.basemaps.cartocdn.com/"
            "light_all/{z}/{x}/{y}.png"
        ),
        attribution=(
            "© OpenStreetMap contributors © CARTO"
        )
    )
)


# ============================================================
# TASK 13
# MAGNITUDE COLOUR MAPPER
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],
    low=float(df["mag"].min()),
    high=float(df["mag"].max())
)


# ============================================================
# TASK 14
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
# TASK 15
# COLOUR BAR
# ============================================================

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


# ============================================================
# TASK 16
# HOVER TOOL
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
# TASK 17
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

    width=220
)


# ============================================================
# TASK 18
# DATE RANGE SLIDER
#
# IMPORTANT:
# The slider uses millisecond timestamps.
#
# step = 1 day
#
# This allows the two handles to be moved independently
# and stopped at dates in the middle of the range.
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=min_time,

    end=max_time,

    value=(
        min_time,
        max_time
    ),

    step=86400000,

    width=500,

    show_value=True,

    tooltips=True
)


# ============================================================
# TASK 19
# STATUS DISPLAY
# ============================================================

status = Div(
    text=(
        "<b>Risk:</b> All"
        "<br>"
        "<b>Earthquakes shown:</b> "
        + str(len(df))
    ),

    width=500
)


# ============================================================
# TASK 20
# JAVASCRIPT FILTER
# ============================================================

filter_callback = CustomJS(
    args={
        "full_source": full_source,
        "source": source,
        "slider": date_slider,
        "risk_filter": risk_filter,
        "status": status
    },

    code="""

    // ========================================================
    // GET ALL EARTHQUAKE DATA
    // ========================================================

    const full = full_source.data;


    // ========================================================
    // GET CURRENT SLIDER VALUES
    //
    // Bokeh DateRangeSlider returns milliseconds.
    // ========================================================

    const start = Number(slider.value[0]);
    const end = Number(slider.value[1]);


    // ========================================================
    // GET CURRENT RISK
    // ========================================================

    const selectedRisk = risk_filter.value;


    // ========================================================
    // CREATE EMPTY RESULT
    // ========================================================

    const result = {
        x: [],
        y: [],
        place: [],
        mag: [],
        time_str: [],
        risk: [],
        time_ms: []
    };


    // ========================================================
    // LOOP THROUGH ALL EARTHQUAKES
    // ========================================================

    for (let i = 0; i < full.x.length; i++) {

        const earthquakeTime =
            Number(full.time_ms[i]);

        const earthquakeRisk =
            String(full.risk[i]);


        // ====================================================
        // CHECK TIME
        // ====================================================

        const timeOK =
            earthquakeTime >= start &&
            earthquakeTime <= end;


        // ====================================================
        // CHECK RISK
        // ====================================================

        let riskOK = true;

        if (selectedRisk !== "All") {

            riskOK =
                earthquakeRisk === selectedRisk;
        }


        // ====================================================
        // APPLY BOTH FILTERS
        // ====================================================

        if (timeOK && riskOK) {

            result.x.push(
                full.x[i]
            );

            result.y.push(
                full.y[i]
            );

            result.place.push(
                full.place[i]
            );

            result.mag.push(
                full.mag[i]
            );

            result.time_str.push(
                full.time_str[i]
            );

            result.risk.push(
                full.risk[i]
            );

            result.time_ms.push(
                full.time_ms[i]
            );
        }
    }


    // ========================================================
    // UPDATE MAP
    // ========================================================

    source.data = result;


    // ========================================================
    // UPDATE STATUS
    // ========================================================

    status.text =
        "<b>Risk:</b> "
        + selectedRisk
        + "<br>"
        + "<b>Earthquakes shown:</b> "
        + result.x.length;
    """
)


# ============================================================
# TASK 21
# CONNECT RISK FILTER
# ============================================================

risk_filter.js_on_change(
    "value",
    filter_callback
)


# ============================================================
# TASK 22
# CONNECT DATE SLIDER
#
# IMPORTANT:
# Use "value", NOT "value_throttled".
#
# This means the dashboard updates while the slider
# is being moved.
# ============================================================

date_slider.js_on_change(
    "value",
    filter_callback
)


# ============================================================
# TASK 23
# CONTROLS
# ============================================================

controls = column(
    risk_filter,

    date_slider,

    status,

    width=550
)


# ============================================================
# TASK 24
# FINAL LAYOUT
# ============================================================

layout = row(
    controls,
    p,

    sizing_mode="stretch_width"
)


# ============================================================
# TASK 25
# BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
