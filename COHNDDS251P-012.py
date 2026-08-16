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
# TASK 2: CONVERT TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# TASK 3: DATE AND TIME
# ============================================================

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms",
    errors="coerce",
    utc=True
)

# Remove timezone information
gdf["time_dt"] = gdf["time_dt"].dt.tz_convert(None)

# Create readable date/time for HoverTool
gdf["time_str"] = gdf["time_dt"].dt.strftime(
    "%Y-%m-%d %H:%M:%S"
)


# ============================================================
# TASK 4: MAGNITUDE
# ============================================================

gdf["mag"] = pd.to_numeric(
    gdf["mag"],
    errors="coerce"
)

gdf["mag"] = gdf["mag"].fillna(0)


# ============================================================
# TASK 5: RISK CLASSIFICATION
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
# TASK 6: PREPARE DATA
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
# CREATE ROW ID
# ============================================================

df["row_id"] = range(len(df))


# ============================================================
# CREATE UNIX TIMESTAMP
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 10**6
)


# ============================================================
# DISPLAY INFORMATION
# ============================================================

print("======================================")
print("USGS EARTHQUAKE DASHBOARD")
print("======================================")

print("Total records:", len(df))

print("\nRisk counts:")
print(df["risk"].value_counts())

print("\nMinimum date:")
print(df["time_dt"].min())

print("\nMaximum date:")
print(df["time_dt"].max())

print("======================================")


# ============================================================
# TASK 7: BOKEH DATA SOURCE
# ============================================================

source = ColumnDataSource(df)


# ============================================================
# TASK 8: BOKEH INDEX FILTER
# ============================================================

index_filter = IndexFilter(
    indices=list(range(len(df)))
)

view = CDSView(
    filter=index_filter
)


# ============================================================
# TASK 9: CREATE MAP
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
# TASK 10: BASE MAP
# ============================================================

p.add_tile(
    WMTSTileSource(
        url="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors © CARTO"
    )
)


# ============================================================
# TASK 11: MAGNITUDE COLOUR MAPPER
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],

    low=float(df["mag"].min()),

    high=float(df["mag"].max())
)


# ============================================================
# TASK 12: EARTHQUAKE POINTS
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
# TASK 13: COLOUR BAR
# ============================================================

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


# ============================================================
# TASK 14: HOVER TOOL
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
# TASK 15: TIME RANGE SLIDER
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=df["time_dt"].min().to_pydatetime(),

    end=df["time_dt"].max().to_pydatetime(),

    value=(
        df["time_dt"].min().to_pydatetime(),
        df["time_dt"].max().to_pydatetime()
    ),

    step=24 * 60 * 60 * 1000,

    width=350
)


# ============================================================
# TASK 16: RISK FILTER
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
# TASK 17: STATUS DISPLAY
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
# TASK 18: FILTER FUNCTION
# ============================================================

def update(attr, old, new):

    # --------------------------------------------------------
    # GET SELECTED RISK
    # --------------------------------------------------------

    selected_risk = risk_filter.value


    # --------------------------------------------------------
    # GET SELECTED DATES
    # --------------------------------------------------------

    start_ms = int(
        pd.Timestamp(
            date_slider.value[0]
        ).timestamp() * 1000
    )

    end_ms = int(
        pd.Timestamp(
            date_slider.value[1]
        ).timestamp() * 1000
    )


    # --------------------------------------------------------
    # TIME FILTER
    # --------------------------------------------------------

    time_condition = (
        (df["time_ms"] >= start_ms)
        &
        (df["time_ms"] <= end_ms)
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

    final_condition = (
        time_condition
        &
        risk_condition
    )


    # --------------------------------------------------------
    # GET SELECTED ROWS
    # --------------------------------------------------------

    selected_rows = df.loc[
        final_condition,
        "row_id"
    ].tolist()


    # --------------------------------------------------------
    # UPDATE MAP
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
# TASK 19: CONNECT RISK FILTER
# ============================================================

risk_filter.on_change(
    "value",
    update
)


# ============================================================
# TASK 20: CONNECT TIME SLIDER
# ============================================================

date_slider.on_change(
    "value",
    update
)


# ============================================================
# TASK 21: DASHBOARD CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# TASK 22: DASHBOARD LAYOUT
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# TASK 23: BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
