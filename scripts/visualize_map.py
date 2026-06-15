#!/usr/bin/env python3
"""
Génère une carte HTML interactive des communes de Madagascar
colorée par région, avec tooltip commune/district/région.
"""

import json
import folium
import random

from pathlib import Path
ROOT         = Path(__file__).resolve().parent.parent
GEOJSON_PATH = ROOT / "data/processed/communes_madagascar.geojson"
OUT_HTML     = ROOT / "output/map_communes_madagascar.html"

# Palette de couleurs distinctes pour les 22 régions
REGION_COLORS = [
    "#E63946", "#457B9D", "#2A9D8F", "#E9C46A", "#F4A261",
    "#264653", "#A8DADC", "#6A0572", "#F77F00", "#D62828",
    "#023E8A", "#80B918", "#7B2D8B", "#FF6B6B", "#4ECDC4",
    "#556B2F", "#FF8C00", "#1D3557", "#9B2335", "#3D5A80",
    "#B5838D", "#6D6875",
]

print("Chargement des données...")
with open(GEOJSON_PATH, encoding="utf-8") as f:
    geojson = json.load(f)

# Construire la palette région → couleur
regions = sorted(set(
    feat["properties"]["region"]
    for feat in geojson["features"]
    if feat["properties"]["region"]
))
color_map = {r: REGION_COLORS[i % len(REGION_COLORS)] for i, r in enumerate(regions)}
print(f"  {len(regions)} régions, {len(geojson['features'])} communes")

# Carte centrée sur Madagascar
m = folium.Map(
    location=[-19.5, 46.8],
    zoom_start=6,
    tiles="CartoDB positron",
    prefer_canvas=True,
)

# Couche GeoJSON avec style + tooltip
def style_fn(feature):
    region = feature["properties"].get("region")
    color = color_map.get(region, "#AAAAAA")
    return {
        "fillColor": color,
        "color": "#555555",
        "weight": 0.4,
        "fillOpacity": 0.65,
    }

def highlight_fn(feature):
    return {
        "fillColor": "#FFFF00",
        "color": "#000000",
        "weight": 1.5,
        "fillOpacity": 0.85,
    }

tooltip = folium.GeoJsonTooltip(
    fields=["shapeName", "district", "region"],
    aliases=["Commune :", "District :", "Région :"],
    localize=True,
    sticky=True,
    style="font-size:13px; font-family:sans-serif;",
)

folium.GeoJson(
    geojson,
    name="Communes",
    style_function=style_fn,
    highlight_function=highlight_fn,
    tooltip=tooltip,
).add_to(m)

# Légende des régions
legend_html = """
<div style="
    position: fixed; bottom: 30px; left: 30px; z-index: 1000;
    background: white; border-radius: 8px; padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    font-family: sans-serif; font-size: 12px;
    max-height: 420px; overflow-y: auto;
">
  <b style="font-size:13px;">Régions de Madagascar</b><br><br>
"""
for region in regions:
    color = color_map[region]
    legend_html += f'<div style="margin:3px 0;"><span style="display:inline-block;width:14px;height:14px;background:{color};border-radius:3px;margin-right:6px;vertical-align:middle;"></span>{region}</div>\n'
legend_html += "</div>"

m.get_root().html.add_child(folium.Element(legend_html))

# Titre
n_communes = len(geojson["features"])
title_html = f"""
<div style="
    position: fixed; top: 15px; left: 50%; transform: translateX(-50%);
    z-index: 1000; background: white; border-radius: 8px;
    padding: 8px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    font-family: sans-serif; font-size: 15px; font-weight: bold;
">
    Madagascar — Communes par Région ({n_communes} communes)
</div>
"""
m.get_root().html.add_child(folium.Element(title_html))

folium.LayerControl().add_to(m)

m.save(OUT_HTML)
print(f"\nCarte générée → {OUT_HTML}")
print("Ouvrez ce fichier dans votre navigateur.")
