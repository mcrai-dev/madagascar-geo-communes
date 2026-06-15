# madagascar-geo-communes

Données géographiques des **1 558 communes de Madagascar** enrichies avec région et district, prêtes à l'emploi pour la cartographie et l'analyse spatiale.

Produit dans le cadre des travaux cartographiques du **BNGRC** (Bureau National de Gestion des Risques et des Catastrophes).

---

## Structure du projet

madagascar-geo-communes/
├── data/
│   ├── raw/                                        # Sources brutes (non modifiées)
│   │   ├── geoBoundaries-MDG-ADM1.geojson          # 22 régions
│   │   ├── geoBoundaries-MDG-ADM2.geojson          # 119 districts  [~28 MB, non versionné]
│   │   ├── geoBoundaries-MDG-ADM3-all/             # Communes brutes BNGRC/OCHA 2020  [non versionné]
│   │   ├── geoBoundaries-MDG-ADM4-all/             # 17 465 fokontany  [non versionné]
│   │   └── liste_commune_par_district.json         # Référence officielle région→district→commune
│   └── processed/
│       └── communes_madagascar.geojson             #  Fichier principal — 1 558 communes
├── scripts/
│   ├── build_communes_map.py                       # Génère communes_madagascar.geojson
│   └── visualize_map.py                            # Génère la carte HTML interactive
├── output/                                         # Carte HTML générée (non versionnée)
├── .gitignore
└── README.md

---

## Fichier principal

### `data/processed/communes_madagascar.geojson`

GeoJSON contenant les **1 558 communes** de Madagascar avec leurs polygones (géométries simplifiées) et les attributs suivants :

| Propriété   | Type   | Description                      |
| ------------- | ------ | -------------------------------- |
| `shapeName` | string | Nom de la commune                |
| `region`    | string | Région (22 régions)            |
| `district`  | string | District (119 districts)         |
| `shapeID`   | string | Identifiant unique geoBoundaries |
| `shapeType` | string | `ADM3`                         |

**Exemple :**

```json
{
  "type": "Feature",
  "properties": {
    "shapeName": "Antsirabe",
    "region":    "Vakinankaratra",
    "district":  "Antsirabe I",
    "shapeID":   "12599549B...",
    "shapeType": "ADM3"
  },
  "geometry": { "type": "Polygon", "coordinates": [...] }
}
```

---

## Utilisation

### Prérequis

```bash
pip install geopandas shapely folium
```

### Reconstruire le GeoJSON depuis les sources brutes

```bash
python scripts/build_communes_map.py
```

> Requiert `data/raw/geoBoundaries-MDG-ADM1.geojson`, `ADM2.geojson`, `ADM3-all/` et `liste_commune_par_district.json`.
> Les fichiers ADM2, ADM3, ADM4 sont téléchargeables sur [geoboundaries.org](https://www.geoboundaries.org) et [HDX](https://data.humdata.org/dataset/madagascar-administrative-level-0-4-boundaries).

### Générer la carte HTML interactive

```bash
python scripts/visualize_map.py
# → output/map_communes_madagascar.html
```

Ouvrez le fichier HTML dans un navigateur — aucun serveur requis.

---

## Méthodologie

### Sources

| Source                                                                | Niveau                 | Utilisation                                |
| --------------------------------------------------------------------- | ---------------------- | ------------------------------------------ |
| [geoBoundaries](https://www.geoboundaries.org) (BNGRC / OCHA ROSA, 2020) | ADM1, ADM2, ADM3, ADM4 | Polygones géographiques                   |
| [julkwel/madagascar-map](https://github.com/julkwel/madagascar-map)      | —                     | Référence région → district → commune |

### Pipeline

1. **Jointure spatiale** — centroïde de chaque commune ADM3 testé contre les polygones ADM1 (régions) et ADM2 (districts) via `geopandas.sjoin`
2. **Vérification croisée** — comparaison avec la liste de référence pour détecter les incohérences
3. **Corrections manuelles** — fusion des entités non-communes identifiées

### Corrections appliquées

Le dataset geoBoundaries ADM3 inclut des arrondissements et fokontany urbains classifiés à tort comme communes. Les entités suivantes ont été fusionnées dans leur commune officielle après vérification Wikipedia et croisement avec la liste BNGRC :

| Entités fusionnées | Commune résultante | Vérification                                       |
| -------------------- | ------------------- | --------------------------------------------------- |
| Mahabibo             | Mahajanga           | fokontany de Mahajanga                              |
| 6 arrondissements    | Antsirabe           | 1 commune, 2 arrondissements (Wikipedia)            |
| 7 arrondissements    | Fianarantsoa        | 1 commune, 7 arrondissements (Wikipedia)            |
| 6 arrondissements    | Toliara I           | "composé de la seule ville de Toliara" (Wikipedia) |
| 5 arrondissements    | Nosy-Be             | 1 commune urbaine, 5 arrondissements (Wikipedia)    |

**Total : 25 entités non-communes supprimées** (1 579 → 1 558 communes).

---

## Hiérarchie administrative de Madagascar

```
ADM1 → Région      (22)
ADM2 → District    (119)
ADM3 → Commune     (1 558)   ← ce dépôt
ADM4 → Fokontany   (17 465)
```

---

## Licence

Les données geoBoundaries sont sous licence **CC BY 3.0 IGO**.
Référence requise : *Runfola, D. et al. (2020). geoBoundaries: A global database of political administrative boundaries. PLoS ONE 15(4): e0231866.*
# madagascar-geo-communes
# madagascar-geo-communes
