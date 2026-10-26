"""Final outputs: cleaned shortlist table and the final project map.
Run after run_pipeline.py and land_based.py: python scripts/final_outputs.py"""
import sys, textwrap
from pathlib import Path
import pandas as pd, geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from matplotlib.colors import LinearSegmentedColormap, Normalize
from matplotlib.cm import ScalarMappable
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PROC, TABLES, MAPS = ROOT / "data" / "processed", ROOT / "outputs" / "tables", ROOT / "MAPS"
QUANTILE, MIN_OUTSIDE_PCT = 0.75, 50
BORDER_SHARE_MARGIN, BORDER_LAND_PCT = 0.5, 60

for p in (PROC / "lsoa_share.gpkg", PROC / "exclusion.gpkg", PROC / "starbucks_bng.gpkg",
          PROC / "outside.gpkg", TABLES / "shortlist_land_based.csv"):
    if not p.exists():
        sys.exit(f"Missing {p.name}: run scripts/run_pipeline.py and scripts/land_based.py first")

g = gpd.read_file(PROC / "lsoa_share.gpkg")
thr = g["share_25_34"].quantile(QUANTILE)
sel = pd.read_csv(TABLES / "shortlist_land_based.csv")

print("1. Cleaned table")
def reasons(r):
    out = []
    if r["share_25_34"] < thr + BORDER_SHARE_MARGIN:
        out.append(f"share within {BORDER_SHARE_MARGIN} points of the cut off")
    if r["outside_pct"] < BORDER_LAND_PCT:
        out.append(f"under {BORDER_LAND_PCT}% of land outside the zone")
    return "; ".join(out)

sel["borderline_reason"] = sel.apply(reasons, axis=1)
sel["borderline"] = sel["borderline_reason"] != ""
final = pd.DataFrame({
    "Rank": range(1, len(sel) + 1),
    "LSOA code": sel["LSOA21CD"],
    "Neighbourhood": sel["LSOA21NM"],
    "Share aged 25 to 34 (%)": sel["share_25_34"],
    "Land outside 1 mile zone (%)": sel["outside_pct"],
    "Land outside 1 mile zone (km2)": sel["outside_km2"],
    "Status": sel["fully_outside"].map({True: "Fully outside zone", False: "Partly inside zone"}),
    "Borderline": sel["borderline"].map({True: "Yes", False: "No"}),
    "Borderline reason": sel["borderline_reason"],
})
final.to_csv(TABLES / "final_shortlist.csv", index=False)
print("Cut off:", round(thr, 2), "| Areas:", len(final), "| Borderline:", int(sel["borderline"].sum()))
print(final.drop(columns=["Borderline reason"]).to_string(index=False))

print("2. Final map")
ex = gpd.read_file(PROC / "exclusion.gpkg")
st = gpd.read_file(PROC / "starbucks_bng.gpkg")
out = gpd.read_file(PROC / "outside.gpkg").dissolve(by="a_LSOA21CD")
codes = list(sel["LSOA21CD"])
land = out.loc[out.index.isin(codes)]
land = land.assign(share=land.index.map(g.set_index("LSOA21CD")["share_25_34"]))
vmin, vmax = thr, land["share"].max()
cmap = LinearSegmentedColormap.from_list("share_green", ["#c7e9d4", "#0b5d3b"])
names = dict(zip(sel["LSOA21CD"], sel["LSOA21NM"].str.replace("Southampton ", "")))
border = dict(zip(sel["LSOA21CD"], sel["borderline"]))

offsets = {"010C": (-65, -35), "010A": (45, -25), "032D": (-75, -10), "014B": (75, -35),
           "031C": (80, 22), "031G": (80, 0), "015E": (-65, -5)}
halo = [pe.withStroke(linewidth=3, foreground="white")]

minx, miny, maxx, maxy = g.total_bounds
pad, pad_bottom = 150, 900
map_h = 9.8 * (maxy - miny + pad + pad_bottom) / (maxx - minx + 2 * pad)
fig, ax = plt.subplots(figsize=(10, map_h + 1.1))
fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=1 - 0.9 / (map_h + 1.1))
g.plot(ax=ax, color="#eeeeee", edgecolor="white", linewidth=0.5)
ex.plot(ax=ax, color="#d85a30", alpha=0.25)
g[g["LSOA21CD"].isin(codes)].plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, linestyle="--")
land.plot(ax=ax, column="share", cmap=cmap, vmin=vmin, vmax=vmax, edgecolor="black", linewidth=0.8)
st.plot(ax=ax, color="black", marker="*", markersize=150)
for code, r in land.iterrows():
    nm = names[code]
    p = r.geometry.representative_point()
    dx, dy = offsets.get(nm, (0, 0))
    ax.annotate(nm + ("*" if border[code] else ""), (p.x, p.y), xytext=(dx, dy),
                textcoords="offset points", ha="center", fontsize=9, weight="bold",
                path_effects=halo, arrowprops=dict(arrowstyle="-", lw=0.6) if (dx or dy) else None)

ax.set_xlim(minx - pad, maxx + pad)
ax.set_ylim(miny - pad_bottom, maxy + pad)
nx = maxx
ax.text(nx, maxy, "N", ha="center", va="top", fontsize=11, weight="bold")
ax.annotate("", xy=(nx, maxy - 450), xytext=(nx, maxy - 1900),
            arrowprops=dict(arrowstyle="-|>", color="black", lw=1.5))
sy = miny - 450
ax.plot([maxx - 2000, maxx], [sy, sy], color="black", lw=2, solid_capstyle="butt")
for xx in (maxx - 2000, maxx):
    ax.plot([xx, xx], [sy - 70, sy + 70], color="black", lw=1.5)
ax.text(maxx - 1000, sy + 180, "2 km", ha="center", fontsize=9)

ax.legend(handles=[
    Patch(facecolor="none", edgecolor="black", linestyle="--", label="Full extent of a partly covered area"),
    Patch(facecolor="#d85a30", alpha=0.25, label="1 mile from a Starbucks"),
    Line2D([0], [0], marker="*", color="w", markerfacecolor="black", markersize=14, label="Starbucks"),
], loc="lower left", bbox_to_anchor=(0.0, 0.14), framealpha=0.4)
cax = ax.inset_axes([0.02, 0.04, 0.26, 0.025])
cb = fig.colorbar(ScalarMappable(norm=Normalize(vmin=vmin, vmax=vmax), cmap=cmap),
                  cax=cax, orientation="horizontal")
ticks = np.linspace(vmin, vmax, 4)
cb.set_ticks(ticks)
cb.set_ticklabels([f"{t:.1f}" for t in ticks])
cb.ax.tick_params(labelsize=8)
cb.ax.set_title("Share aged 25 to 34 (%)\nshortlisted land outside the zone", fontsize=8, loc="left", pad=3)
ax.set_axis_off()
ax.set_title("Where to open a new coffee shop in Southampton (hypothetical screening)\n"
             "Neighbourhoods with many residents aged 25 to 34 and most of their land "
             "more than 1 mile from a Starbucks",
             fontsize=11)

notes = [
    f"High = top quartile of the share of residents aged 25 to 34 across all {len(g)} Southampton LSOAs "
    f"({thr:.1f}% or more). Shortlisted when at least {MIN_OUTSIDE_PCT}% of an area lies outside the zone. "
    "Each share describes the whole area.",
    f"* Borderline: share within {BORDER_SHARE_MARGIN} points of the cut off, or under {BORDER_LAND_PCT}% of land outside the zone.",
    "Hypothetical scenario. The four Starbucks locations were identified manually in Google Maps. "
    "Buffer, dissolve and overlay run with terrio v0.5.0 in British National Grid (EPSG:27700).",
    "Contains Census 2021 data from the Office for National Statistics and boundaries from the ONS Open Geography Portal "
    "(Open Government Licence v3.0). Contains Ordnance Survey data. Crown copyright and database right 2021.",
]
fig.text(0.02, 0.0, "\n".join(textwrap.fill(n, 125) for n in notes), va="top", ha="left", fontsize=8)

target = MAPS / "final_map_1mile.png"
try:
    plt.savefig(target, dpi=200, bbox_inches="tight")
except OSError:
    sys.exit(f"Could not save {target}: close the image if it is open in a viewer, then run again")
print("Saved", target)
print("Saved", TABLES / "final_shortlist.csv")