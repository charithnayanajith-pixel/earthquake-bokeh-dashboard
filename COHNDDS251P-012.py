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
# 3. DATE / TIME
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
# 6. PREPARE DATA
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
# 7. NUMERIC TIME
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 10**6
)


# ============================================================
# 8. CREATE TWO DATA SOURCES
#
# full_source = original complete data
# source      = data currently displayed
# ============================================================

full_source = ColumnDataSource(df)

source = ColumnDataSource(df.copy())


# ============================================================
# 9. CREATE MAP
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
# 10. BASE MAP
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
# 11. COLOUR MAPPER
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],

    low=float(df["mag"].min()),

    high=float(df["mag"].max())
)


# ============================================================
# 12. EARTHQUAKE POINTS
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
# 13. COLOUR BAR
# ============================================================

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


# ============================================================
# 14. HOVER TOOL
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
# 15. FIND MINIMUM AND MAXIMUM DATE
# ============================================================

min_time = int(df["time_ms"].min())

max_time = int(df["time_ms"].max())


# ============================================================
# 16. DATE RANGE SLIDER
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=min_time,

    end=max_time,

    value=(min_time, max_time),

    step=24 * 60 * 60 * 1000,

    width=350
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

    width=200
)


# ============================================================
# 18. STATUS DISPLAY
# ============================================================

status = Div(
    text=(
        "<b>Risk:</b> All"
        "<br>"
        "<b>Earthquakes shown:</b> "
        + str(len(df))
    ),

    width=300
)


# ============================================================
# 19. JAVASCRIPT FILTER
# ============================================================

callback = CustomJS(
    args=dict(
        full_source=full_source,
        source=source,
        slider=date_slider,
        risk_select=risk_filter,
        status=status
    ),

    code="""

    // --------------------------------------------------------
    // GET ORIGINAL DATA
    // --------------------------------------------------------

    const full = full_source.data;

    const start = slider.value[0];

    const end = slider.value[1];

    const selectedRisk = risk_select.value;


    // --------------------------------------------------------
    // CREATE EMPTY RESULT
    // --------------------------------------------------------

    const result = {
        x: [],
        y: [],
        place: [],
        mag: [],
        time_dt: [],
        time_str: [],
        risk: [],
        time_ms: []
    };


    // --------------------------------------------------------
    // LOOP THROUGH ALL EARTHQUAKES
    // --------------------------------------------------------

    for (let i = 0; i < full.x.length; i++) {

        const earthquakeTime = full.time_ms[i];

        const earthquakeRisk = full.risk[i];


        // ----------------------------------------------------
        // TIME CONDITION
        // ----------------------------------------------------

        const timeOK =
            earthquakeTime >= start &&
            earthquakeTime <= end;


        // ----------------------------------------------------
        // RISK CONDITION
        // ----------------------------------------------------

        let riskOK = true;

        if (selectedRisk !== "All") {
            riskOK = earthquakeRisk === selectedRisk;
        }


        // ----------------------------------------------------
        // BOTH CONDITIONS
        // ----------------------------------------------------

        if (timeOK && riskOK) {

            result.x.push(full.x[i]);

            result.y.push(full.y[i]);

            result.place.push(full.place[i]);

            result.mag.push(full.mag[i]);

            result.time_dt.push(full.time_dt[i]);

            result.time_str.push(full.time_str[i]);

            result.risk.push(full.risk[i]);

            result.time_ms.push(full.time_ms[i]);
        }
    }


    // --------------------------------------------------------
    // UPDATE MAP
    // --------------------------------------------------------

    source.data = result;


    // --------------------------------------------------------
    // UPDATE STATUS
    // --------------------------------------------------------

    status.text =
        "<b>Risk:</b> " +
        selectedRisk +
        "<br>" +
        "<b>Earthquakes shown:</b> " +
        result.x.length;
    """
)


# ============================================================
# 20. CONNECT CALLBACK TO RISK FILTER
# ============================================================

risk_filter.js_on_change(
    "value",
    callback
)


# ============================================================
# 21. CONNECT CALLBACK TO TIME SLIDER
# ============================================================

date_slider.js_on_change(
    "value",
    callback
)


# ============================================================
# 22. CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# 23. FINAL DASHBOARD
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# 24. BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
