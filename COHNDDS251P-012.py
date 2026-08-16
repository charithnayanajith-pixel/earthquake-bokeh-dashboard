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
    CustomJS,
    Div
)
from bokeh.palettes import YlOrRd
from bokeh.layouts import row, column


# ============================================================
# TASK 1: IMPORT GEOSPATIAL DATA
# ============================================================

url = (
    "https://earthquake.usgs.gov/earthquakes/"
    "feed/v1.0/summary/all_month.geojson"
)

gdf = gpd.read_file(url)


# ============================================================
# TASK 2: GEOPANDAS + BOKEH MAP
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# TIME DATA
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
# MAGNITUDE
# ============================================================

gdf["mag"] = pd.to_numeric(
    gdf["mag"],
    errors="coerce"
)

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
).reset_index(drop=True)


# ============================================================
# TIME IN MILLISECONDS
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 1_000_000
).astype("int64")


# ============================================================
# ACTUAL DATA RANGE
#
# This is the important correction.
# The slider covers the dates that actually exist
# in the USGS monthly dataset.
# ============================================================

min_date = (
    df["time_dt"]
    .dt.tz_convert(None)
    .min()
    .to_pydatetime()
)

max_date = (
    df["time_dt"]
    .dt.tz_convert(None)
    .max()
    .to_pydatetime()
)


# ============================================================
# COMPLETE DATA SOURCE
# ============================================================

full_source = ColumnDataSource(
    data={
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "place": df["place"].fillna("Unknown").tolist(),
        "mag": df["mag"].astype(float).tolist(),
        "time_str": df["time_str"].tolist(),
        "time_ms": df["time_ms"].tolist(),
        "risk": df["risk"].tolist()
    }
)


# ============================================================
# DISPLAY DATA SOURCE
# ============================================================

source = ColumnDataSource(
    data={
        "x": df["x"].tolist(),
        "y": df["y"].tolist(),
        "place": df["place"].fillna("Unknown").tolist(),
        "mag": df["mag"].astype(float).tolist(),
        "time_str": df["time_str"].tolist(),
        "time_ms": df["time_ms"].tolist(),
        "risk": df["risk"].tolist()
    }
)


# ============================================================
# TASK 2: CREATE MAP
# ============================================================

p = figure(
    title="USGS Earthquake Interactive Geo Dashboard",

    x_axis_type="mercator",
    y_axis_type="mercator",

    x_range=(-20000000, 20000000),
    y_range=(-10000000, 10000000),

    width=900,
    height=600,

    tools=(
        "pan,"
        "wheel_zoom,"
        "box_zoom,"
        "reset,"
        "save"
    )
)


# ============================================================
# BASEMAP
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
# TASK 4: MAGNITUDE COLOUR MAPPING
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],
    low=float(df["mag"].min()),
    high=float(df["mag"].max())
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

    line_color="black",

    line_width=0.5
)


# ============================================================
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

    start=min_date,

    end=max_date,

    value=(
        min_date,
        max_date
    ),

    step=1,

    width=500,

    show_value=True,

    tooltips=True
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

    width=220
)


# ============================================================
# STATUS
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

    width=500
)


# ============================================================
# FILTER CALLBACK
# ============================================================

callback = CustomJS(
    args={
        "full_source": full_source,
        "source": source,
        "slider": date_slider,
        "risk_filter": risk_filter,
        "status": status
    },

    code="""

    // Complete dataset
    const full = full_source.data;


    // Selected date range
    const start = Number(slider.value[0]);
    const end = Number(slider.value[1]);


    // Selected risk
    const selectedRisk = risk_filter.value;


    // Empty filtered dataset
    const result = {
        x: [],
        y: [],
        place: [],
        mag: [],
        time_str: [],
        time_ms: [],
        risk: []
    };


    // Filter records
    for (let i = 0; i < full.x.length; i++) {

        const earthquakeTime =
            Number(full.time_ms[i]);

        const earthquakeRisk =
            String(full.risk[i]);


        // Date condition
        const dateOK =
            earthquakeTime >= start &&
            earthquakeTime <= end;


        // Risk condition
        let riskOK = true;

        if (selectedRisk !== "All") {
            riskOK =
                earthquakeRisk === selectedRisk;
        }


        // Apply both filters
        if (dateOK && riskOK) {

            result.x.push(full.x[i]);
            result.y.push(full.y[i]);
            result.place.push(full.place[i]);
            result.mag.push(full.mag[i]);
            result.time_str.push(full.time_str[i]);
            result.time_ms.push(full.time_ms[i]);
            result.risk.push(full.risk[i]);
        }
    }


    // Update map
    source.data = result;


    // Display selected dates
    const startText =
        new Date(start).toLocaleDateString(
            "en-GB",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );

    const endText =
        new Date(end).toLocaleDateString(
            "en-GB",
            {
                day: "2-digit",
                month: "short",
                year: "numeric"
            }
        );


    // Update status
    status.text =
        "<b>Risk:</b> "
        + selectedRisk
        + "<br>"
        + "<b>Start Date:</b> "
        + startText
        + "<br>"
        + "<b>End Date:</b> "
        + endText
        + "<br>"
        + "<b>Earthquakes shown:</b> "
        + result.x.length;
    """
)


# ============================================================
# CONNECT RISK FILTER
# ============================================================

risk_filter.js_on_change(
    "value",
    callback
)


# ============================================================
# CONNECT TIME FILTER
# ============================================================

date_slider.js_on_change(
    "value",
    callback
)


# ============================================================
# CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status,
    width=550
)


# ============================================================
# FINAL DASHBOARD
# ============================================================

layout = row(
    controls,
    p,
    sizing_mode="stretch_width"
)


# ============================================================
# TASK 5: BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
