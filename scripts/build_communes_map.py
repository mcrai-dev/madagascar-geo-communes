#!/usr/bin/env python3
"""
Build a Madagascar commune GeoJSON enriched with region and district attributes.
Strategy:
  1. Spatial join ADM3 communes with ADM1 regions + ADM2 districts
  2. Fill remaining gaps using name matching against liste_commune_par_district.json
"""

import json
import unicodedata
import re
import geopandas as gpd
from shapely.geometry import shape

from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

ADM1_PATH = ROOT / "data/raw/geoBoundaries-MDG-ADM1.geojson"
ADM2_PATH = ROOT / "data/raw/geoBoundaries-MDG-ADM2.geojson"
ADM3_PATH = ROOT / "data/raw/geoBoundaries-MDG-ADM3-all/geoBoundaries-MDG-ADM3_simplified.geojson"
REF_PATH  = ROOT / "data/raw/liste_commune_par_district.json"
OUT_PATH  = ROOT / "data/processed/communes_madagascar.geojson"


def normalize(s):
    s = s.strip().upper()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[-\s]+", " ", s)
    return s


def build_name_lookup(ref):
    """Build normalized name → [{region, district, commune}] from reference JSON."""
    lookup = {}
    for region, districts in ref.items():
        if region == "Region":
            continue
        for district, communes in districts.items():
            for commune in communes:
                key = normalize(commune)
                entry = {"region": region, "district": district, "commune": commune}
                lookup.setdefault(key, []).append(entry)
    return lookup


print("Loading data...")
adm1 = gpd.read_file(ADM1_PATH)
adm2 = gpd.read_file(ADM2_PATH)
adm3 = gpd.read_file(ADM3_PATH)

# Ensure same CRS
adm1 = adm1.to_crs("EPSG:4326")
adm2 = adm2.to_crs("EPSG:4326")
adm3 = adm3.to_crs("EPSG:4326")

print(f"  ADM1 (regions):   {len(adm1)} features")
print(f"  ADM2 (districts): {len(adm2)} features")
print(f"  ADM3 (communes):  {len(adm3)} features")

# ── Step 1: Spatial join using commune centroids ─────────────────────────────
print("\nStep 1: Spatial join via centroids...")
adm3_centroids = adm3.copy()
adm3_centroids["geometry"] = adm3.geometry.centroid

joined_district = gpd.sjoin(
    adm3_centroids[["shapeName", "shapeID", "geometry"]],
    adm2[["shapeName", "geometry"]].rename(columns={"shapeName": "district_sj"}),
    how="left",
    predicate="within"
)
joined_region = gpd.sjoin(
    adm3_centroids[["shapeName", "shapeID", "geometry"]],
    adm1[["shapeName", "geometry"]].rename(columns={"shapeName": "region_sj"}),
    how="left",
    predicate="within"
)

# Merge back into a single lookup by shapeID
district_map = (
    joined_district[["shapeID", "district_sj"]]
    .drop_duplicates("shapeID")
    .set_index("shapeID")["district_sj"]
    .to_dict()
)
region_map = (
    joined_region[["shapeID", "region_sj"]]
    .drop_duplicates("shapeID")
    .set_index("shapeID")["region_sj"]
    .to_dict()
)

spatial_matched = sum(1 for v in district_map.values() if v is not None and str(v) != "nan")
print(f"  Districts assigned spatially: {spatial_matched}/{len(adm3)}")

# ── Step 2: Name-based fallback from reference JSON ──────────────────────────
print("\nStep 2: Name-based fallback for missing assignments...")
with open(REF_PATH) as f:
    ref = json.load(f)
lookup = build_name_lookup(ref)

fallback_count = 0
for _, row in adm3.iterrows():
    sid = row["shapeID"]
    if district_map.get(sid) and str(district_map[sid]) != "nan":
        continue
    key = normalize(row["shapeName"])
    if key in lookup and len(lookup[key]) == 1:
        district_map[sid] = lookup[key][0]["district"]
        region_map[sid]   = lookup[key][0]["region"]
        fallback_count += 1

print(f"  Additional via name match: {fallback_count}")

# ── Step 3: Build enriched GeoJSON ───────────────────────────────────────────
print("\nStep 3: Building output GeoJSON...")

with open(ADM3_PATH) as f:
    raw = json.load(f)

stats = {"region": 0, "district": 0, "none": 0}
for feat in raw["features"]:
    sid = feat["properties"]["shapeID"]
    region   = region_map.get(sid)
    district = district_map.get(sid)

    if region and str(region) != "nan":
        stats["region"] += 1
    if district and str(district) != "nan":
        stats["district"] += 1
    else:
        stats["none"] += 1

    feat["properties"]["region"]   = region if region and str(region) != "nan" else None
    feat["properties"]["district"] = district if district and str(district) != "nan" else None

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, separators=(",", ":"))

print(f"\nDone → {OUT_PATH}")
print(f"  With region:   {stats['region']}/{len(raw['features'])}")
print(f"  With district: {stats['district']}/{len(raw['features'])}")
print(f"  Missing:       {stats['none']}/{len(raw['features'])}")

# ── Step 4: Show unresolved features ─────────────────────────────────────────
missing = [
    f["properties"]["shapeName"]
    for f in raw["features"]
    if not f["properties"]["district"]
]
if missing:
    print(f"\nUnresolved communes ({len(missing)}):")
    for n in missing:
        print(f"  - {n}")
