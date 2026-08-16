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
    IndexFilter,
    CDSView,
    Div
)
from bokeh.palettes import YlOrRd
from bokeh.layouts import row, column


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

# Remove timezone information
gdf["time_dt"] = gdf["time_dt"].dt.tz_localize(None)

gdf["time_str"] = gdf["time_dt"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
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
# CREATE PERMANENT ROW ID
# ============================================================

df["row_id"] = range(len(df))


# ============================================================
# DISPLAY DATA INFORMATION IN TERMINAL
# ============================================================

print("---------------------------------------")
print("USGS EARTHQUAKE DATA")
print("---------------------------------------")

print("Total earthquakes:", len(df))

print("\nRisk counts:")
print(df["risk"].value_counts())

print("\nDate range:")
print(df["time_dt"].min())
print(df["time_dt"].max())

print("---------------------------------------")


# ============================================================
# BOKEH DATA SOURCE
# ============================================================

source = ColumnDataSource(df)


# ============================================================
# BOKEH INDEX FILTER
# ============================================================

index_filter = IndexFilter(
    indices=list(range(len(df)))
)

view = CDSView(
    filter=index_filter
)


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
# BASE MAP
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

    view=view,

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
# TIME SLIDER
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
# RISK SELECT
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
# STATUS DISPLAY
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
# UPDATE FUNCTION
# ============================================================

def update(attr, old, new):

    # --------------------------------------------------------
    # GET SELECTED RISK
    # --------------------------------------------------------

    selected_risk = risk_filter.value


    # --------------------------------------------------------
    # GET SELECTED DATES
    # --------------------------------------------------------

    start_date = pd.Timestamp(
        date_slider.value[0]
    )

    end_date = pd.Timestamp(
        date_slider.value[1]
    )


    # --------------------------------------------------------
    # CREATE BOOLEAN FILTER
    # --------------------------------------------------------

    mask = (
        (df["time_dt"] >= start_date)
        &
        (df["time_dt"] <= end_date)
    )


    # --------------------------------------------------------
    # APPLY RISK FILTER
    # --------------------------------------------------------

    if selected_risk != "All":

        mask = (
            mask
            &
            (df["risk"] == selected_risk)
        )


    # --------------------------------------------------------
    # GET ROW IDS
    # --------------------------------------------------------

    selected_rows = df.loc[
        mask,
        "row_id"
    ].tolist()


    # --------------------------------------------------------
    # UPDATE BOKEH FILTER
    # --------------------------------------------------------

    index_filter.indices = selected_rows


    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    status.text = (
        "<b>Risk:</b> "
        + selected_risk
        + "<br>"
        + "<b>Earthquakes shown:</b> "
        + str(len(selected_rows))
    )


# ============================================================
# CALLBACKS
# ============================================================

risk_filter.on_change(
    "value",
    update
)

date_slider.on_change(
    "value",
    update
)


# ============================================================
# CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# DASHBOARD
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
