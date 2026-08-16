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
# 2. CONVERT GEOMETRY TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# 3. CONVERT EARTHQUAKE TIME
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
# 7. CONVERT TIME TO INTEGER MILLISECONDS
#
# This is the ONLY time representation used by the filters.
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 1_000_000
).astype("int64")


# ============================================================
# 8. MINIMUM / MAXIMUM TIME
# ============================================================

min_time = int(df["time_ms"].min())
max_time = int(df["time_ms"].max())


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
        "time_ms": df["time_ms"].tolist()
    }
)


# ============================================================
# 10. DISPLAY DATA SOURCE
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
# 11. CREATE MAP
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
# 12. BASE MAP
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
# 13. MAGNITUDE COLOUR MAPPER
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
# 16. HOVER TOOL
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
# 17. DATE RANGE SLIDER
#
# Bokeh DateRangeSlider uses milliseconds internally.
# Therefore we deliberately give it integer milliseconds.
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=min_time,

    end=max_time,

    value=(
        min_time,
        max_time
    ),

    step=24 * 60 * 60 * 1000,

    width=400
)


# ============================================================
# 18. RISK FILTER
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
# 19. STATUS
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
# 20. JAVASCRIPT FILTER
# ============================================================

callback = CustomJS(
    args=dict(
        full_source=full_source,
        source=source,
        slider=date_slider,
        risk_filter=risk_filter,
        status=status
    ),

    code="""

    // ========================================================
    // GET COMPLETE DATA
    // ========================================================

    const full = full_source.data;


    // ========================================================
    // GET SLIDER VALUES
    //
    // DateRangeSlider returns milliseconds.
    // ========================================================

    const start = Number(slider.value[0]);

    const end = Number(slider.value[1]);


    // ========================================================
    // GET RISK
    // ========================================================

    const selectedRisk = risk_filter.value;


    // ========================================================
    // EMPTY RESULT
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
    // FILTER DATA
    // ========================================================

    for (let i = 0; i < full.x.length; i++) {

        const earthquakeTime =
            Number(full.time_ms[i]);

        const earthquakeRisk =
            String(full.risk[i]);


        // ----------------------------------------------------
        // TIME FILTER
        // ----------------------------------------------------

        const timeMatches =
            earthquakeTime >= start &&
            earthquakeTime <= end;


        // ----------------------------------------------------
        // RISK FILTER
        // ----------------------------------------------------

        let riskMatches = true;

        if (selectedRisk !== "All") {

            riskMatches =
                earthquakeRisk === selectedRisk;
        }


        // ----------------------------------------------------
        // BOTH FILTERS
        // ----------------------------------------------------

        if (timeMatches && riskMatches) {

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
# 21. RISK CALLBACK
# ============================================================

risk_filter.js_on_change(
    "value",
    callback
)


# ============================================================
# 22. TIME SLIDER CALLBACK
# ============================================================

date_slider.js_on_change(
    "value",
    callback
)


# ============================================================
# 23. CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# 24. FINAL LAYOUT
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# 25. START BOKEH
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
