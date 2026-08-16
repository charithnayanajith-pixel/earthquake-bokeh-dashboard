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
# 1. LOAD USGS EARTHQUAKE DATA
# ============================================================

url = (
    "https://earthquake.usgs.gov/earthquakes/"
    "feed/v1.0/summary/all_month.geojson"
)

gdf = gpd.read_file(url)


# ============================================================
# 2. CONVERT COORDINATES TO WEB MERCATOR
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
# 5. RISK LEVEL
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
# 7. CREATE MILLISECOND TIME COLUMN
# ============================================================

df["time_ms"] = (
    df["time_dt"].astype("int64") // 10**6
)


# ============================================================
# 8. CREATE ROW INDEX
# ============================================================

df["row_index"] = range(len(df))


# ============================================================
# 9. INITIAL DATA SOURCE
# ============================================================

source = ColumnDataSource(df)


# ============================================================
# 10. CREATE INDEX FILTER
# ============================================================

index_filter = IndexFilter(
    indices=list(range(len(df)))
)


# ============================================================
# 11. CREATE CDS VIEW
# ============================================================

view = CDSView(
    filter=index_filter
)


# ============================================================
# 12. CREATE MAP
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
# 13. ADD BASE MAP
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
# 16. COLOUR BAR
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

minimum_time = int(df["time_ms"].min())
maximum_time = int(df["time_ms"].max())

date_slider = DateRangeSlider(
    title="Time Filter",

    start=minimum_time,

    end=maximum_time,

    value=(
        minimum_time,
        maximum_time
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
# 21. FILTER FUNCTION
# ============================================================

def update(attr, old, new):

    # --------------------------------------------------------
    # GET TIME RANGE
    # --------------------------------------------------------

    start_time = int(date_slider.value[0])
    end_time = int(date_slider.value[1])


    # --------------------------------------------------------
    # GET RISK
    # --------------------------------------------------------

    selected_risk = risk_filter.value


    # --------------------------------------------------------
    # TIME CONDITION
    # --------------------------------------------------------

    time_condition = (
        (df["time_ms"] >= start_time)
        &
        (df["time_ms"] <= end_time)
    )


    # --------------------------------------------------------
    # RISK CONDITION
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
    # COMBINE CONDITIONS
    # --------------------------------------------------------

    final_condition = (
        time_condition
        &
        risk_condition
    )


    # --------------------------------------------------------
    # FIND ROW INDICES
    # --------------------------------------------------------

    selected_indices = df.index[
        final_condition
    ].tolist()


    # --------------------------------------------------------
    # UPDATE BOKEH VIEW
    # --------------------------------------------------------

    index_filter.indices = selected_indices


    # --------------------------------------------------------
    # UPDATE STATUS
    # --------------------------------------------------------

    status.text = (
        "<b>Risk:</b> "
        + selected_risk
        + "<br>"
        + "<b>Earthquakes shown:</b> "
        + str(len(selected_indices))
    )


# ============================================================
# 22. CONNECT RISK FILTER
# ============================================================

risk_filter.on_change(
    "value",
    update
)


# ============================================================
# 23. CONNECT TIME SLIDER
# ============================================================

date_slider.on_change(
    "value",
    update
)


# ============================================================
# 24. CONTROLS
# ============================================================

controls = column(
    risk_filter,
    date_slider,
    status
)


# ============================================================
# 25. FINAL LAYOUT
# ============================================================

layout = row(
    controls,
    p
)


# ============================================================
# 26. START BOKEH APPLICATION
# ============================================================

curdoc().add_root(layout)

curdoc().title = "USGS Earthquake Dashboard"
