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
# 3. CREATE DATE/TIME
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
# 6. PREPARE DATAFRAME
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
# 7. CREATE NUMERIC TIME COLUMN
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 10**6
)


# ============================================================
# 8. BOKEH DATA SOURCE
# ============================================================

source = ColumnDataSource(df)


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
# 15. DATE RANGE SLIDER
# ============================================================

min_date = df["time_dt"].min().to_pydatetime()

max_date = df["time_dt"].max().to_pydatetime()


date_slider = DateRangeSlider(
    title="Time Filter",

    start=min_date,

    end=max_date,

    value=(
        min_date,
        max_date
    ),

    step=24 * 60 * 60 * 1000,

    width=350
)


# ============================================================
# 16. RISK FILTER
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
# 17. STATUS DISPLAY
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
# 18. UPDATE FUNCTION
# ============================================================

def update(attr, old, new):

    # --------------------------------------------------------
    # GET DATE RANGE FROM SLIDER
    # --------------------------------------------------------

    start_date = pd.to_datetime(
        date_slider.value[0]
    )

    end_date = pd.to_datetime(
        date_slider.value[1]
    )


    # --------------------------------------------------------
    # GET RISK
    # --------------------------------------------------------

    selected_risk = risk_filter.value


    # --------------------------------------------------------
    # TIME FILTER
    # --------------------------------------------------------

    time_condition = (
        (df["time_dt"] >= start_date)
        &
        (df["time_dt"] <= end_date)
    )


    # --------------------------------------------------------
    # RISK FILTER
    # --------------------------------------------------------

    if selected_risk == "All":

        risk_condition = pd.Series(
            True,
            index=df.index
        )

    else:

        risk_condition = (
            df["risk"] == selected_risk
        )


    # --------------------------------------------------------
    # COMBINE FILTERS
    # --------------------------------------------------------

    filtered = df[
        time_condition & risk_condition
    ]


    # --------------------------------------------------------
    # UPDATE DATA SOURCE
    # --------------------------------------------------------

    source.data = (
        ColumnDataSource
        .from_df(filtered)
    )


    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    status.text = (
        "<b>Risk:</b> "
        + selected_risk
        + "<br>"
        + "<b>Earthquakes shown:</b> "
        + str(len(filtered))
    )


# ============================================================
# 19. CONNECT RISK FILTER
# ============================================================

risk_filter.on_change(
    "value",
    update
)


# ============================================================
# 20. CONNECT TIME SLIDER
# ============================================================

date_slider.on_change(
    "value",
    update
)


# ============================================================
# 21. CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# 22. FINAL DASHBOARD
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# 23. BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
