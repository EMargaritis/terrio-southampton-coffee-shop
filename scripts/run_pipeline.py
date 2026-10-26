"""Southampton site screening: share aged 25 to 34, outside 1 mile of every Starbucks.
Run from anywhere: python scripts/run_pipeline.py"""
import shutil, subprocess, sys
from pathlib import Path
import pandas as pd, geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
RAW, PROC = ROOT / "data" / "raw", ROOT / "data" / "processed"
TABLES, MAPS = ROOT / "outputs" / "tables", ROOT / "MAPS"
CRS, DISTANCE_M, QUANTILE = 27700, 1609.34, 0.75

for d in (PROC, TABLES, MAPS, MAPS / "sensitivity"):
    d.mkdir(parents=True, exist_ok=True)
if shutil.which("terrio") is None:
    sys.exit("terrio was not found on the PATH")


def run_terrio(*args):
    Path(args[-1]).unlink(missing_ok=True)
    subprocess.run(["terrio", *[str(a) for a in args]], check=True)


print("1. Census data and boundaries")
t = pd.read_csv(RAW / "census2021-ts007a-lsoa.csv")
tot = [c for c in t.columns if "Total" in c]
bands = [c for c in t.columns if "25 to 29" in c or "30 to 34" in c]
assert len(tot) == 1 and len(bands) == 2, (tot, bands)
t["share_25_34"] = t[bands].sum(axis=1) / t[tot[0]] * 100
t = t.rename(columns={"geography code": "LSOA21CD"})
g = gpd.read_file(RAW / "lsoa_soton.geojson")
g = g[g["LSOA21NM"].str.startswith("Southampton")]
g = g.merge(t[["LSOA21CD", "share_25_34"]], on="LSOA21CD", how="left")
assert len(g) == 152 and g["share_25_34"].notna().all()
g = g.to_crs(CRS)
lsoa_path = PROC / "lsoa_share.gpkg"
lsoa_path.unlink(missing_ok=True)
g.to_file(lsoa_path, driver="GPKG")

print("2. Starbucks points")
st = gpd.read_file(RAW / "starbucks.geojson").to_crs(CRS)
assert len(st) == 4
st_path = PROC / "starbucks_bng.gpkg"
st_path.unlink(missing_ok=True)
st.to_file(st_path, driver="GPKG")

print("3. terrio: buffer, dissolve, overlay")
buf = PROC / "starbucks_buf.gpkg"
excl = PROC / "exclusion.gpkg"
cov_path = PROC / "covered.gpkg"
run_terrio("buffer", "--distance", DISTANCE_M, st_path, buf)
run_terrio("dissolve", buf, excl)
run_terrio("overlay", "--operation", "intersection", lsoa_path, excl, cov_path)

print("4. Coverage and ranking")
cov = gpd.read_file(cov_path).dissolve(by="a_LSOA21CD").area
g["covered_pct"] = g["LSOA21CD"].map(cov).fillna(0) / g.area * 100
thr = g["share_25_34"].quantile(QUANTILE)
sel = g[(g["covered_pct"] == 0) & (g["share_25_34"] >= thr)]
sel = sel.sort_values("share_25_34", ascending=False)
out = sel[["LSOA21CD", "LSOA21NM", "share_25_34"]].round(1)
out.to_csv(TABLES / "shortlist.csv", index=False)
sel_path = PROC / "shortlist.gpkg"
sel_path.unlink(missing_ok=True)
sel.to_file(sel_path, driver="GPKG")
print("Threshold:", round(thr, 2), "| Areas with any overlap:", int((g["covered_pct"] > 0).sum()))
print("Shortlisted:", len(sel))
print(out.to_string(index=False))
print("Check against earlier result (8 areas):", "PASS" if len(sel) == 8 else "FAIL")

print("5. Map")
ex = gpd.read_file(excl)
offsets = {"010C": (-65, -35), "010A": (45, -25), "032D": (-50, 25)}
halo = [pe.withStroke(linewidth=3, foreground="white")]
fig, ax = plt.subplots(figsize=(10, 10))
g.plot(ax=ax, color="#eeeeee", edgecolor="white", linewidth=0.5)
ex.plot(ax=ax, color="#d85a30", alpha=0.25)
sel.plot(ax=ax, color="#1d9e75", edgecolor="black", linewidth=0.8)
st.plot(ax=ax, color="black", marker="*", markersize=150)
for _, r in sel.iterrows():
    name = r["LSOA21NM"].replace("Southampton ", "")
    p = r.geometry.representative_point()
    dx, dy = offsets.get(name, (0, 0))
    ax.annotate(name, (p.x, p.y), xytext=(dx, dy), textcoords="offset points",
                ha="center", fontsize=9, weight="bold", path_effects=halo,
                arrowprops=dict(arrowstyle="-", lw=0.6) if (dx or dy) else None)
ax.legend(handles=[
    Patch(facecolor="#1d9e75", edgecolor="black", label="Shortlisted areas"),
    Patch(facecolor="#d85a30", alpha=0.25, label="1 mile from a Starbucks"),
    Line2D([0], [0], marker="*", color="w", markerfacecolor="black", markersize=14, label="Starbucks"),
], loc="lower left")
ax.set_axis_off()
ax.set_title("Top quartile share aged 25 to 34, outside 1 mile of Starbucks")
plt.savefig(MAPS / "sensitivity" / "primary_map_1mile.png", dpi=200, bbox_inches="tight")
print("Saved", MAPS / "sensitivity" / "primary_map_1mile.png")