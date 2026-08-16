#!/usr/bin/env python
# coding: utf-8

import geopandas as gpd
import pandas as pd

from bokeh.io import curdoc
from bokeh.plotting import figure

from bokeh.models import (
    ColumnDataSource,
    HoverTool,
    DateSlider,
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
# 1. LOAD USGS EARTHQUAKE DATA
# ============================================================

url = (
    "https://earthquake.usgs.gov/earthquakes/"
    "feed/v1.0/summary/all_month.geojson"
)

gdf = gpd.read_file(url)


# ============================================================
# 2. CONVERT TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# 3. CONVERT TIME
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
# 4. MAGNITUDE
# ============================================================

gdf["mag"] = pd.to_numeric(
    gdf["mag"],
    errors="coerce"
)

gdf["mag"] = gdf["mag"].fillna(0)


# ============================================================
# 5. RISK CLASSIFICATION
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
# 6. CLEAN DATA
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
# 7. CREATE DATE-ONLY COLUMN
#
# We deliberately use dates rather than Unix milliseconds
# for the filter logic.
# ============================================================

df["date_only"] = (
    df["time_dt"]
    .dt.tz_convert(None)
    .dt.normalize()
)


# ============================================================
# 8. DATE VALUES FOR BOKEH
#
# DateSlider works with milliseconds internally.
# ============================================================

min_date = df["date_only"].min()
max_date = df["date_only"].max()

min_ms = int(min_date.timestamp() * 1000)
max_ms = int(max_date.timestamp() * 1000)


# ============================================================
# 9. COMPLETE DATA SOURCE
# ============================================================

full_source = ColumnDataSource(
    data={
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "place": df["place"].tolist(),
        "mag": df["mag"].tolist(),
        "time_str": df["time_str"].tolist(),
        "risk": df["risk"].tolist(),

        # Date stored as milliseconds
        "date_ms": (
            df["date_only"]
            .astype("int64")
            // 1_000_000
        ).tolist()
    }
)


# ============================================================
# 10. DISPLAY SOURCE
# ============================================================

source = ColumnDataSource(
    data={
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "place": df["place"].tolist(),
        "mag": df["mag"].tolist(),
        "time_str": df["time_str"].tolist(),
        "risk": df["risk"].tolist(),

        "date_ms": (
            df["date_only"]
            .astype("int64")
            // 1_000_000
        ).tolist()
    }
)


# ============================================================
# 11. MAP
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
# 12. BASEMAP
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
# 13. COLOUR MAPPER
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],

    low=float(df["mag"].min()),

    high=float(df["mag"].max())
)


# ============================================================
# 14. EARTHQUAKE POINTS
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
# 15. COLOUR BAR
# ============================================================

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


# ============================================================
# 16. HOVER
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
# 17. RISK FILTER
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

    width=300
)


# ============================================================
# 18. START DATE SLIDER
# ============================================================

start_slider = DateSlider(
    title="Start Date",

    start=min_ms,

    end=max_ms,

    value=min_ms,

    step=86400000,

    width=450
)


# ============================================================
# 19. END DATE SLIDER
# ============================================================

end_slider = DateSlider(
    title="End Date",

    start=min_ms,

    end=max_ms,

    value=max_ms,

    step=86400000,

    width=450
)


# ============================================================
# 20. STATUS
# ============================================================

status = Div(
    text=(
        "<b>Risk:</b> All"
        "<br>"
        "<b>Start Date:</b> "
        + min_date.strftime("%d %b %Y")
        + "<br>"
        "<b>End Date:</b> "
        + max_date.strftime("%d %b %Y")
        + "<br>"
        "<b>Earthquakes shown:</b> "
        + str(len(df))
    ),

    width=450
)


# ============================================================
# 21. JAVASCRIPT FILTER
# ============================================================

callback = CustomJS(
    args={
        "full_source": full_source,
        "source": source,
        "risk_filter": risk_filter,
        "start_slider": start_slider,
        "end_slider": end_slider,
        "status": status
    },

    code="""

    // ========================================================
    // GET ALL DATA
    // ========================================================

    const full = full_source.data;


    // ========================================================
    // GET SLIDER VALUES
    // ========================================================

    let start = Number(start_slider.value);

    let end = Number(end_slider.value);


    // ========================================================
    // PREVENT INVALID DATE RANGE
    // ========================================================

    if (start > end) {

        source.data = {
            x: [],
            y: [],
            place: [],
            mag: [],
            time_str: [],
            risk: [],
            date_ms: []
        };

        status.text =
            "<b>Invalid date range.</b>"
            + "<br>"
            + "Start Date must be before End Date.";

        return;
    }


    // ========================================================
    // SELECTED RISK
    // ========================================================

    const selectedRisk =
        risk_filter.value;


    // ========================================================
    // RESULT
    // ========================================================

    const result = {
        x: [],
        y: [],
        place: [],
        mag: [],
        time_str: [],
        risk: [],
        date_ms: []
    };


    // ========================================================
    // FILTER DATA
    // ========================================================

    for (let i = 0; i < full.x.length; i++) {

        const earthquakeDate =
            Number(full.date_ms[i]);

        const earthquakeRisk =
            String(full.risk[i]);


        // ----------------------------------------------------
        // DATE FILTER
        // ----------------------------------------------------

        const dateOK =
            earthquakeDate >= start &&
            earthquakeDate <= end;


        // ----------------------------------------------------
        // RISK FILTER
        // ----------------------------------------------------

        let riskOK = true;

        if (selectedRisk !== "All") {

            riskOK =
                earthquakeRisk === selectedRisk;
        }


        // ----------------------------------------------------
        // BOTH FILTERS
        // ----------------------------------------------------

        if (dateOK && riskOK) {

            result.x.push(full.x[i]);

            result.y.push(full.y[i]);

            result.place.push(full.place[i]);

            result.mag.push(full.mag[i]);

            result.time_str.push(
                full.time_str[i]
            );

            result.risk.push(
                full.risk[i]
            );

            result.date_ms.push(
                full.date_ms[i]
            );
        }
    }


    // ========================================================
    // UPDATE MAP
    // ========================================================

    source.data = result;


    // ========================================================
    // FORMAT DATES
    // ========================================================

    const startDate =
        new Date(start).toLocaleDateString(
            "en-GB",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );

    const endDate =
        new Date(end).toLocaleDateString(
            "en-GB",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );


    // ========================================================
    // UPDATE STATUS
    // ========================================================

    status.text =
        "<b>Risk:</b> "
        + selectedRisk
        + "<br>"
        + "<b>Start Date:</b> "
        + startDate
        + "<br>"
        + "<b>End Date:</b> "
        + endDate
        + "<br>"
        + "<b>Earthquakes shown:</b> "
        + result.x.length;
    """
)


# ============================================================
# 22. CONNECT RISK FILTER
# ============================================================

risk_filter.js_on_change(
    "value",
    callback
)


# ============================================================
# 23. CONNECT START DATE
# ============================================================

start_slider.js_on_change(
    "value",
    callback
)


# ============================================================
# 24. CONNECT END DATE
# ============================================================

end_slider.js_on_change(
    "value",
    callback
)


# ============================================================
# 25. CONTROLS
# ============================================================

controls = column(
    risk_filter,

    start_slider,

    end_slider,

    status,

    width=500
)


# ============================================================
# 26. FINAL LAYOUT
# ============================================================

layout = row(
    controls,
    p,

    sizing_mode="stretch_width"
)


# ============================================================
# 27. BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
