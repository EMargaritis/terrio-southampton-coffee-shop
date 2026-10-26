"""Export the shortlist as one small GeoJSON (WGS84) for the web dashboard.
Run after final_outputs.py: python scripts/export_dashboard_data.py"""
import sys
from pathlib import Path
import pandas as pd, geopandas as gpd

ROOT = Path(__file__).resolve().parent.parent
PROC, TABLES = ROOT / "data" / "processed", ROOT / "outputs" / "tables"
OUT = ROOT / "outputs" / "dashboard_data.geojson"

for p in (PROC / "outside.gpkg", PROC / "lsoa_share.gpkg", PROC / "exclusion.gpkg",
          PROC / "starbucks_bng.gpkg", TABLES / "final_shortlist.csv"):
    if not p.exists():
        sys.exit(f"Missing {p.name}: run the earlier scripts first")

tbl = pd.read_csv(TABLES / "final_shortlist.csv").rename(columns={
    "Rank": "rank", "LSOA code": "code", "Neighbourhood": "name",
    "Share aged 25 to 34 (%)": "share", "Land outside 1 mile zone (%)": "outside_pct",
    "Land outside 1 mile zone (km2)": "outside_km2", "Status": "status",
    "Borderline": "borderline", "Borderline reason": "reason"})
tbl["reason"] = tbl["reason"].fillna("")
codes = list(tbl["code"])

out = gpd.read_file(PROC / "outside.gpkg").dissolve(by="a_LSOA21CD")
land = out.loc[out.index.isin(codes), ["geometry"]].reset_index().rename(columns={"a_LSOA21CD": "code"})
land = land.merge(tbl, on="code", how="left").assign(layer="land")

g = gpd.read_file(PROC / "lsoa_share.gpkg")
extent = g.loc[g["LSOA21CD"].isin(codes), ["LSOA21CD", "geometry"]].rename(columns={"LSOA21CD": "code"})
extent = extent.merge(tbl[["code", "name"]], on="code", how="left").assign(layer="extent")

zone = gpd.read_file(PROC / "exclusion.gpkg")[["geometry"]].assign(layer="zone", name="1 mile from a Starbucks")
st = gpd.read_file(PROC / "starbucks_bng.gpkg")[["geometry"]].reset_index(drop=True)
st = st.assign(layer="store", name=[f"Starbucks {i + 1}" for i in range(len(st))])

allf = pd.concat([land, extent, zone, st], ignore_index=True)
allf = gpd.GeoDataFrame(allf, geometry="geometry", crs=g.crs)
allf["geometry"] = allf.geometry.simplify(3, preserve_topology=True)
allf = allf.to_crs(4326)
OUT.unlink(missing_ok=True)
allf.to_file(OUT, driver="GeoJSON", COORDINATE_PRECISION=6)
print(allf["layer"].value_counts().to_string())
print("Saved", OUT, "|", round(OUT.stat().st_size / 1024, 1), "KB")