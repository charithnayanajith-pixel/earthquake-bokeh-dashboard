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
# 1. IMPORT USGS EARTHQUAKE DATA
# ============================================================

url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"

gdf = gpd.read_file(url)


# ============================================================
# 2. CONVERT COORDINATES TO WEB MERCATOR
# ============================================================

gdf = gdf.to_crs(epsg=3857)

gdf["x"] = gdf.geometry.x
gdf["y"] = gdf.geometry.y


# ============================================================
# 3. CREATE DATETIME
# ============================================================

gdf["time_dt"] = pd.to_datetime(
    gdf["time"],
    unit="ms",
    errors="coerce",
    utc=True
)

# Remove timezone
gdf["time_dt"] = gdf["time_dt"].dt.tz_convert(None)

# Text version for HoverTool
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
# 7. CREATE INTEGER ROW ID
# ============================================================

df["row_id"] = range(len(df))


# ============================================================
# 8. CREATE UNIX TIME COLUMN
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 10**6
)


# ============================================================
# 9. PRINT INFORMATION
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

print("\nMinimum timestamp:")
print(df["time_ms"].min())

print("\nMaximum timestamp:")
print(df["time_ms"].max())

print("======================================")


# ============================================================
# 10. BOKEH DATA SOURCE
# ============================================================

source = ColumnDataSource(df)


# ============================================================
# 11. BOKEH FILTER
# ============================================================

index_filter = IndexFilter(
    indices=list(range(len(df)))
)

view = CDSView(
    filter=index_filter
)


# ============================================================
# 12. MAP
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
# 13. BASE MAP
# ============================================================

p.add_tile(
    WMTSTileSource(
        url="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png",
        attribution="© OpenStreetMap contributors © CARTO"
    )
)


# ============================================================
# 14. COLOUR MAPPER
# ============================================================

mapper = LinearColorMapper(
    palette=YlOrRd[9],

    low=float(df["mag"].min()),

    high=float(df["mag"].max())
)


# ============================================================
# 15. EARTHQUAKE POINTS
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
# 16. COLOR BAR
# ============================================================

p.add_layout(
    ColorBar(
        color_mapper=mapper,
        title="Magnitude"
    ),
    "right"
)


# ============================================================
# 17. HOVER TOOL
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
# 18. TIME SLIDER
# ============================================================

date_slider = DateRangeSlider(
    title="Time Filter",

    start=int(df["time_ms"].min()),

    end=int(df["time_ms"].max()),

    value=(
        int(df["time_ms"].min()),
        int(df["time_ms"].max())
    ),

    step=24 * 60 * 60 * 1000,

    width=350
)


# ============================================================
# 19. RISK FILTER
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
# 20. STATUS
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
# 21. UPDATE FUNCTION
# ============================================================

def update(attr, old, new):

    # --------------------------------------------------------
    # GET SELECTED RISK
    # --------------------------------------------------------

    selected_risk = risk_filter.value


    # --------------------------------------------------------
    # GET SLIDER VALUES
    # --------------------------------------------------------

    start_ms = date_slider.value[0]

    end_ms = date_slider.value[1]


    # --------------------------------------------------------
    # CREATE TIME FILTER
    # --------------------------------------------------------

    time_condition = (
        (df["time_ms"] >= start_ms)
        &
        (df["time_ms"] <= end_ms)
    )


    # --------------------------------------------------------
    # CREATE RISK FILTER
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
    # GET ROW IDS
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
# 22. CALLBACKS
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
# 23. CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# 24. DASHBOARD LAYOUT
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# 25. BOKEH SERVER
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
