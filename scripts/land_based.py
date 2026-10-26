"""Land based exclusion: cut the 1 mile zone out of each area with terrio, then keep
high share areas with at least 50 per cent of their land outside the zone.
Run after run_pipeline.py: python scripts/land_based.py"""
import shutil, subprocess, sys
from pathlib import Path
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
PROC, TABLES, MAPS = ROOT / "data" / "processed", ROOT / "outputs" / "tables", ROOT / "MAPS"
QUANTILE, MIN_OUTSIDE_PCT = 0.75, 50

if shutil.which("terrio") is None:
    sys.exit("terrio was not found on the PATH")
for f in ("lsoa_share.gpkg", "exclusion.gpkg", "starbucks_bng.gpkg", "covered.gpkg"):
    if not (PROC / f).exists():
        sys.exit(f"Missing {f}: run scripts/run_pipeline.py first")

print("1. terrio: difference (cut the zone out of each area)")
outside_path = PROC / "outside.gpkg"
outside_path.unlink(missing_ok=True)
subprocess.run(["terrio", "overlay", "--operation", "difference",
                str(PROC / "lsoa_share.gpkg"), str(PROC / "exclusion.gpkg"),
                str(outside_path)], check=True)

print("2. Remaining land per area")
g = gpd.read_file(PROC / "lsoa_share.gpkg")
out = gpd.read_file(outside_path).dissolve(by="a_LSOA21CD")
out_area = out.area
g["outside_km2"] = g["LSOA21CD"].map(out_area).fillna(0) / 1e6
g["outside_pct"] = g["LSOA21CD"].map(out_area).fillna(0) / g.area * 100
g["area_km2"] = g.area / 1e6
tot_check = (g["outside_km2"].sum() + gpd.read_file(PROC / "covered.gpkg").area.sum() / 1e6)
print("Area check: outside plus covered =", round(tot_check, 2), "km2; total =", round(g["area_km2"].sum(), 2), "km2")

print("3. Ranking")
thr = g["share_25_34"].quantile(QUANTILE)
sel = g[(g["share_25_34"] >= thr) & (g["outside_pct"] >= MIN_OUTSIDE_PCT)]
sel = sel.sort_values("share_25_34", ascending=False)
sel = sel.assign(fully_outside=sel["outside_pct"] > 99.99)
table = sel[["LSOA21CD", "LSOA21NM", "share_25_34", "outside_pct", "outside_km2", "fully_outside"]].round(1)
table.to_csv(TABLES / "shortlist_land_based.csv", index=False)
print("Threshold:", round(thr, 2), "| Minimum land outside:", MIN_OUTSIDE_PCT, "per cent")
print("Shortlisted:", len(sel), "| of which fully outside the zone:", int(sel["fully_outside"].sum()))
print(table.to_string(index=False))
print("Check (the 8 fully outside areas must all be included):",
      "PASS" if int(sel["fully_outside"].sum()) == 8 else "FAIL")

print("4. Map")
ex = gpd.read_file(PROC / "exclusion.gpkg")
st = gpd.read_file(PROC / "starbucks_bng.gpkg")
land = out.loc[out.index.isin(sel["LSOA21CD"])]
halo = [pe.withStroke(linewidth=3, foreground="white")]
fig, ax = plt.subplots(figsize=(10, 10))
g.plot(ax=ax, color="#eeeeee", edgecolor="white", linewidth=0.5)
ex.plot(ax=ax, color="#d85a30", alpha=0.25)
sel.plot(ax=ax, facecolor="none", edgecolor="black", linewidth=0.6, linestyle="--")
land.plot(ax=ax, color="#1d9e75", edgecolor="black", linewidth=0.8)
st.plot(ax=ax, color="black", marker="*", markersize=150)
offsets = {"010C": (-65, -35), "010A": (45, -25), "032D": (60, -30), "014B": (75, -35), "031C": (80, 22), "031G": (80, 0), "015E": (-65, -5)}
for code, r in land.iterrows():
    name = sel.loc[sel["LSOA21CD"] == code, "LSOA21NM"].iloc[0].replace("Southampton ", "")
    p = r.geometry.representative_point()
    dx, dy = offsets.get(name, (0, 0))
    ax.annotate(name, (p.x, p.y), xytext=(dx, dy), textcoords="offset points",
                ha="center", fontsize=9, weight="bold", path_effects=halo,
                arrowprops=dict(arrowstyle="-", lw=0.6) if (dx or dy) else None)
ax.legend(handles=[
    Patch(facecolor="#1d9e75", edgecolor="black", label="Land outside the zone, shortlisted areas"),
    Patch(facecolor="#d85a30", alpha=0.25, label="1 mile from a Starbucks"),
    Line2D([0], [0], marker="*", color="w", markerfacecolor="black", markersize=14, label="Starbucks"),
], loc="lower left", framealpha=0.4)
ax.set_axis_off()
ax.set_title("Top quartile share aged 25 to 34, with at least 50% of the area outside 1 mile of Starbucks")
plt.savefig(MAPS / "sensitivity" / "primary_map_1mile_land.png", dpi=200, bbox_inches="tight")
print("Saved", MAPS / "sensitivity" / "primary_map_1mile_land.png")