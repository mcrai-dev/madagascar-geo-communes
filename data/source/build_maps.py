#!/usr/bin/env python3
"""
Build:
  1. madagascar-regions-24.geojson  – 24-region polygon GeoJSON
  2. madagascar-numbered.svg        – original map + CSV numbering + names
  3. madagascar-named.svg           – clean feature map (color + name + chef-lieu)
"""

import re, json, math, csv
from pathlib import Path

DATA = Path('/home/mcrai/Projects/BNGRC/finance/fnc-portal/public/data')
SVG_SRC = DATA / 'Regions_of_Madagascar.svg'

# ── 1. Load 24-region CSV ──────────────────────────────────────────────────────
regions = []
with open(DATA / 'madagascar_regions_enriched.csv') as f:
    for row in csv.DictReader(f):
        regions.append({
            'id':       int(row['id']),
            'region':   row['region'],
            'chef_lieu':row['chef_lieu'],
            'lat':      float(row['latitude']),
            'lng':      float(row['longitude']),
        })

# ── 2. Calibration: SVG-pixel → (lng, lat) ────────────────────────────────────
CAL = [
    (587.36, 271.18, 49.2917, -12.2787),
    (686.38, 309.35, 50.1667, -14.2667),
    (554.52, 377.12, 47.9833, -14.8833),
    (329.25, 525.11, 46.3167, -15.7167),
    (419.88, 606.60, 46.8333, -16.9500),
    (545.52, 613.18, 48.4167, -17.8333),
    (625.95, 575.92, 49.4167, -17.3833),
    (204.63, 656.59, 44.0167, -18.0667),
    (335.30, 727.06, 46.0333, -18.7667),
    (436.00, 722.69, 47.5079, -18.8792),
    (572.19, 740.83, 49.4023, -18.1492),
    (392.60, 780.58, 46.8167, -19.0167),
    (193.98, 918.18, 44.2833, -20.2833),
    (386.06, 859.52, 47.0335, -19.8659),
    (392.60, 939.98, 47.2500, -20.5333),
    (363.04,1022.37, 47.0857, -21.4527),
    (468.29,1017.26, 48.2150, -21.7083),
    (300.22,1111.27, 46.1167, -22.4000),
    (149.54,1279.55, 43.6667, -23.3500),
    (234.22,1335.55, 46.0833, -25.1667),
    (343.32,1322.82, 46.9833, -25.0325),
    (386.06,1236.88, 47.8333, -22.8167),
]

def lstsq_fit(cal):
    ATA = [[0.0]*3 for _ in range(3)]
    ATb_lng = [0.0]*3
    ATb_lat = [0.0]*3
    for (x, y, lng, lat) in cal:
        row = [x, y, 1.0]
        for i in range(3):
            ATb_lng[i] += row[i]*lng
            ATb_lat[i] += row[i]*lat
            for j in range(3):
                ATA[i][j] += row[i]*row[j]
    def gauss(M, b):
        aug = [M[i][:]+[b[i]] for i in range(3)]
        for c in range(3):
            p = max(range(c,3), key=lambda r: abs(aug[r][c]))
            aug[c], aug[p] = aug[p], aug[c]
            pv = aug[c][c]
            if abs(pv) < 1e-12: continue
            for r in range(3):
                if r != c:
                    f = aug[r][c]/pv
                    for k in range(4): aug[r][k] -= f*aug[c][k]
        return [aug[i][3]/aug[i][i] if abs(aug[i][i])>1e-12 else 0 for i in range(3)]
    return gauss(ATA, ATb_lng), gauss(ATA, ATb_lat)

C_LNG, C_LAT = lstsq_fit(CAL)

def px2geo(x, y):
    return [round(C_LNG[0]*x+C_LNG[1]*y+C_LNG[2],5),
            round(C_LAT[0]*x+C_LAT[1]*y+C_LAT[2],5)]

def geo2px(lng, lat):
    a1,b1 = C_LNG[0],C_LNG[1]
    a2,b2 = C_LAT[0],C_LAT[1]
    r1 = lng-C_LNG[2]; r2 = lat-C_LAT[2]
    det = a1*b2-a2*b1
    if abs(det)<1e-12: return (400.0,700.0)
    return (round((r1*b2-r2*b1)/det,1), round((a1*r2-a2*r1)/det,1))

# ── 3. Parse SVG — only Regions_1_-1 group (the 22 real region paths) ─────────
svg_text = SVG_SRC.read_text(encoding='utf-8')

r1_match = re.search(r'<g id="Regions_1_-1"[^>]*>(.*?)</g>', svg_text, re.DOTALL)
if not r1_match:
    print("ERROR: Regions_1_-1 not found"); exit(1)
main_group_content = r1_match.group(1)
main_group_full    = r1_match.group(0)

def parse_paths_from(content):
    paths = []
    for m in re.finditer(r'<path\b([^/]*)/>', content, re.DOTALL):
        attrs = m.group(1)
        id_m = re.search(r'id="([^"]+)"', attrs)
        d_m  = re.search(r'\bd="([^"]+)"', attrs)
        if id_m and d_m:
            # Extract fill from style or attribute
            style_m = re.search(r'style="([^"]*)"', attrs)
            fill = '#cccccc'
            if style_m:
                fm = re.search(r'fill:([^;]+)', style_m.group(1))
                if fm: fill = fm.group(1).strip()
            else:
                fm = re.search(r'fill="([^"]+)"', attrs)
                if fm: fill = fm.group(1)
            paths.append({'id':id_m.group(1),'d':d_m.group(1),'fill':fill,'elem':m.group(0)})
    return paths

main_paths = parse_paths_from(main_group_content)
print(f"Found {len(main_paths)} paths in Regions_1_-1")

# ── 4. SVG path parser (M L C c z) → pixel points ────────────────────────────
def cubic_bz(p0, p1, p2, p3, n=10):
    pts = []
    for i in range(n+1):
        t=i/n; mt=1-t
        pts.append((mt**3*p0[0]+3*mt**2*t*p1[0]+3*mt*t**2*p2[0]+t**3*p3[0],
                    mt**3*p0[1]+3*mt**2*t*p1[1]+3*mt*t**2*p2[1]+t**3*p3[1]))
    return pts

def parse_d(d):
    toks = re.findall(r'[MLHVCSQTAZmlhvcsqtaz]|[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?', d)
    pts=[]; cur=(0.0,0.0); start=(0.0,0.0); cmd=None; i=0
    def nxt():
        nonlocal i; v=float(toks[i]); i+=1; return v
    while i<len(toks):
        t=toks[i]
        if re.match(r'[A-Za-z]',t): cmd=t; i+=1; continue
        try:
            if cmd=='M':
                x,y=nxt(),nxt(); cur=(x,y); pts.append(cur); start=cur; cmd='L'
            elif cmd=='m':
                dx,dy=nxt(),nxt(); cur=(cur[0]+dx,cur[1]+dy); pts.append(cur); start=cur; cmd='l'
            elif cmd=='L':
                x,y=nxt(),nxt(); cur=(x,y); pts.append(cur)
            elif cmd=='l':
                dx,dy=nxt(),nxt(); cur=(cur[0]+dx,cur[1]+dy); pts.append(cur)
            elif cmd=='H':
                x=nxt(); cur=(x,cur[1]); pts.append(cur)
            elif cmd=='h':
                dx=nxt(); cur=(cur[0]+dx,cur[1]); pts.append(cur)
            elif cmd=='V':
                y=nxt(); cur=(cur[0],y); pts.append(cur)
            elif cmd=='v':
                dy=nxt(); cur=(cur[0],cur[1]+dy); pts.append(cur)
            elif cmd=='C':
                x1,y1,x2,y2,x,y=nxt(),nxt(),nxt(),nxt(),nxt(),nxt()
                p=cubic_bz(cur,(x1,y1),(x2,y2),(x,y)); pts.extend(p[1:]); cur=(x,y)
            elif cmd=='c':
                d1,e1,d2,e2,dx,dy=nxt(),nxt(),nxt(),nxt(),nxt(),nxt()
                p0=cur; p1=(cur[0]+d1,cur[1]+e1); p2=(cur[0]+d2,cur[1]+e2); p3=(cur[0]+dx,cur[1]+dy)
                p=cubic_bz(p0,p1,p2,p3); pts.extend(p[1:]); cur=p3
            elif cmd in ('S','Q'):
                nxt();nxt();x,y=nxt(),nxt(); cur=(x,y); pts.append(cur)
            elif cmd in ('s','q'):
                nxt();nxt();dx,dy=nxt(),nxt(); cur=(cur[0]+dx,cur[1]+dy); pts.append(cur)
            elif cmd in ('Z','z'):
                if pts and pts[-1]!=start: pts.append(start); cur=start
            else:
                i+=1
        except: i+=1
    return pts

def centroid(pts):
    if not pts: return (0.0,0.0)
    return (sum(p[0] for p in pts)/len(pts), sum(p[1] for p in pts)/len(pts))

parsed=[]
for p in main_paths:
    try:
        pts=parse_d(p['d'])
        if len(pts)<6: continue
        cx,cy=centroid(pts)
        parsed.append({**p,'pts':pts,'cx':cx,'cy':cy})
    except Exception as e:
        print(f"  skip {p['id']}: {e}")
print(f"Parsed {len(parsed)} region paths")

# ── 5. Match paths → CSV regions ──────────────────────────────────────────────
for r in regions:
    r['px'],r['py'] = geo2px(r['lng'],r['lat'])

def sqdist(ax,ay,bx,by): return (ax-bx)**2+(ay-by)**2

used=set()
for path in sorted(parsed, key=lambda p:(p['cy'],p['cx'])):
    best_r,best_d=None,float('inf')
    for r in regions:
        if r['id'] in used: continue
        d=sqdist(path['cx'],path['cy'],r['px'],r['py'])
        if d<best_d: best_d=d; best_r=r
    if best_r:
        path['region']=best_r
        used.add(best_r['id'])

matched=[p for p in parsed if p.get('region')]
unmatched=[r for r in regions if r['id'] not in used]
print(f"Matched {len(matched)} paths, unmatched regions: {[r['region'] for r in unmatched]}")

# Verify
for p in sorted(matched,key=lambda x:x['region']['id']):
    r=p['region']
    g=px2geo(p['cx'],p['cy'])
    err=math.sqrt((g[0]-r['lng'])**2+(g[1]-r['lat'])**2)*111
    status="✓" if err<150 else "⚠"
    print(f"  {status} {r['id']:2d}. {r['region']:<22} err={err:.0f}km")

# ── 6. Build GeoJSON ───────────────────────────────────────────────────────────
features=[]
for path in matched:
    r=path['region']
    raw=path['pts'][::3]; raw.append(raw[0])
    ring=[px2geo(x,y) for x,y in raw]
    features.append({"type":"Feature","properties":{
        "id":r['id'],"region":r['region'],"chef_lieu":r['chef_lieu'],
        "lat":r['lat'],"lng":r['lng']},"geometry":{"type":"Polygon","coordinates":[ring]}})
for r in unmatched:
    features.append({"type":"Feature","properties":{
        "id":r['id'],"region":r['region'],"chef_lieu":r['chef_lieu'],
        "lat":r['lat'],"lng":r['lng']},"geometry":{"type":"Point","coordinates":[r['lng'],r['lat']]}})
features.sort(key=lambda f:f['properties']['id'])
(DATA/'madagascar-regions-24.geojson').write_text(
    json.dumps({"type":"FeatureCollection","features":features},ensure_ascii=False,indent=2))
print(f"\n✓ GeoJSON: madagascar-regions-24.geojson ({len(features)} features)")

# ── 7. Color palette ───────────────────────────────────────────────────────────
PALETTE=["#FFC8C8","#FFD8B0","#FFF5B0","#C8F5C8","#B0DEFF","#DCC8FF",
         "#FFC8EC","#B0F5EE","#FFE4B0","#C8D8FF","#E4FFB0","#FFCCE4",
         "#B8E8FF","#FFE8B8","#B8F5E0","#F0B8FF","#FFE0B8","#B8F0FF",
         "#FFD0C8","#B8FFDE","#F8B8FF","#B8FFCC","#FFB8F5","#CCCEFF"]
def pal(id_): return PALETTE[(id_-1)%len(PALETTE)]

pid2r={p['id']:p['region'] for p in matched}

# ── 8. Colorize paths ──────────────────────────────────────────────────────────
def set_fill(elem,color):
    if re.search(r'style="[^"]*fill:',elem):
        return re.sub(r'(style="[^"]*fill:)[^;"]*(;?)',rf'\g<1>{color}\2',elem)
    if 'fill="' in elem:
        return re.sub(r'fill="[^"]*"',f'fill="{color}"',elem,count=1)
    return elem.replace('/>',f' fill="{color}"/>',1)

colored_content=main_group_content
for path in matched:
    r=path['region']
    color=pal(r['id'])
    colored_content=colored_content.replace(path['elem'], set_fill(path['elem'],color))

colored_group_full=main_group_full.replace(main_group_content,colored_content)

# ── 9. Extract other layers ────────────────────────────────────────────────────
def extract(name):
    """Extract inner content of <g id=name> handling nested <g> groups."""
    m = re.search(rf'<g\b[^>]*\bid="{re.escape(name)}"[^>]*>', svg_text)
    if not m: return ''
    pos = m.end(); depth = 1; i = pos
    while i < len(svg_text) and depth > 0:
        om = re.search(r'<g\b', svg_text[i:])
        cm = re.search(r'</g>', svg_text[i:])
        if not cm: break
        op = om.start() if om else len(svg_text)
        cp = cm.start()
        if op < cp:
            depth += 1; i += op + 2
        else:
            depth -= 1
            if depth == 0: return svg_text[pos: i + cp]
            i += cp + 4
    return ''

coast_inner  =extract('layer5')
borders_inner=extract('layer7')

# ── 10. Build labels ───────────────────────────────────────────────────────────
def labels_numbered():
    lines=['<g id="csv_labels" font-family="Arial,sans-serif">']
    for r in regions:
        sx,sy=geo2px(r['lng'],r['lat'])
        c=pal(r['id'])
        lines.append(f'  <circle cx="{sx}" cy="{sy}" r="14" fill="{c}" stroke="#333" stroke-width="0.8" opacity="0.93"/>')
        lines.append(f'  <text x="{sx}" y="{sy+5}" text-anchor="middle" font-size="12" font-weight="bold" fill="#1a1a2e">{r["id"]}</text>')
        lines.append(f'  <text x="{sx}" y="{sy+23}" text-anchor="middle" font-size="8" fill="#222">{r["region"]}</text>')
    lines.append('</g>')
    return '\n'.join(lines)

def labels_full():
    lines=['<g id="full_labels" font-family="Arial,sans-serif">']
    for r in regions:
        sx,sy=geo2px(r['lng'],r['lat'])
        c=pal(r['id'])
        nm=r['region']; ch=r['chef_lieu']
        fw=max(len(nm),len(ch))*5.6+16
        lines.append(f'''  <g transform="translate({sx},{sy})">
    <rect x="-{fw/2:.0f}" y="-19" width="{fw:.0f}" height="34" rx="4" fill="{c}" stroke="#555" stroke-width="0.6" opacity="0.92"/>
    <text x="0" y="-5" text-anchor="middle" font-size="9.5" font-weight="bold" fill="#1a1a2e">{r["id"]}. {nm}</text>
    <text x="0" y="10" text-anchor="middle" font-size="8" fill="#444">{ch}</text>
  </g>''')
    lines.append('</g>')
    return '\n'.join(lines)

# ── 11. SVG #1: numbered + named (on top of original background) ───────────────
svg1=svg_text

# Disable old number/name layers
for lid in ('Nmbrs_Regions','TT','TT_Regions'):
    svg1=re.sub(rf'(<g id="{lid}"[^>]*display=")[^"]*(")',r'\1none\2',svg1)
    # Also handle if display is not explicitly set (add it)
    if f'id="{lid}"' in svg1 and f'id="{lid}"' in svg1:
        svg1=re.sub(rf'(<g id="{lid}"(?![^>]*display)[^>]*)>',rf'\1 display="none">',svg1)

# Colorize region paths
svg1=svg1.replace(main_group_full, colored_group_full)

# Inject labels before </svg>
svg1=svg1.replace('</svg>', labels_numbered()+'\n</svg>')

svg1 = re.sub(r'\s+inkscape:[a-zA-Z_-]+="[^"]*"', '', svg1)
svg1 = re.sub(r'\s+sodipodi:[a-zA-Z_-]+="[^"]*"', '', svg1)
(DATA/'madagascar-numbered.svg').write_text(svg1,encoding='utf-8')
print("✓ SVG #1: madagascar-numbered.svg")

# ── 12. SVG #2: clean modern feature map ──────────────────────────────────────
W,H=803.127,1458.43
legend_rows=''.join(
    f'    <rect x="8" y="{12+i*16}" width="14" height="11" rx="2" fill="{pal(r["id"])}"/>\n'
    f'    <text x="28" y="{23+i*16}" font-family="Arial,sans-serif" font-size="9" fill="#1a1a2e">{r["id"]}. {r["region"]}</text>\n'
    for i,r in enumerate(regions))

svg2=f'''<?xml version="1.0" encoding="utf-8"?>
<svg version="1.1" xmlns="http://www.w3.org/2000/svg"
     width="{W}px" height="{H}px" viewBox="0 0 {W} {H}">
  <defs>
    <filter id="shadow"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#0002"/></filter>
  </defs>

  <rect width="{W}" height="{H}" fill="#C5E8F5"/>

  <g id="regions" transform="translate(0,-3.97e-5)">
{colored_content}
  </g>

  <g id="coast" stroke="#005FA3" stroke-width="0.8" fill="none" transform="translate(0,-3.97e-5)">
{coast_inner}
  </g>

  <g id="borders" stroke="#555" stroke-width="0.5" fill="none" transform="translate(0,-3.97e-5)">
{borders_inner}
  </g>

{labels_full()}

  <rect x="8" y="8" width="252" height="54" rx="7" fill="white" opacity="0.9" filter="url(#shadow)"/>
  <text x="18" y="32" font-family="Arial,sans-serif" font-size="14" font-weight="bold" fill="#1a1a2e">Madagascar · 24 Régions</text>
  <text x="18" y="50" font-family="Arial,sans-serif" font-size="10" fill="#64748b">Fonds National de Contingence – BNGRC</text>

  <g transform="translate(8,72)">
    <rect width="154" height="{len(regions)*16+14}" rx="5" fill="white" opacity="0.88"/>
{legend_rows}
  </g>
</svg>'''

svg2 = re.sub(r'\s+inkscape:[a-zA-Z_-]+="[^"]*"', '', svg2)
svg2 = re.sub(r'\s+sodipodi:[a-zA-Z_-]+="[^"]*"', '', svg2)
(DATA/'madagascar-named.svg').write_text(svg2,encoding='utf-8')
print("✓ SVG #2: madagascar-named.svg")

# ── 13. region-paths.json (used by the Next.js /cartographie page) ─────────────
APP_CARTO = DATA.parent.parent / 'app' / 'cartographie'
region_paths_out = []
for path in sorted(matched, key=lambda p: p['region']['id']):
    r = path['region']
    region_paths_out.append({
        'pathId':    path['id'],
        'd':         path['d'],
        'id':        r['id'],
        'region':    r['region'],
        'chef_lieu': r['chef_lieu'],
        'lat':       r['lat'],
        'lng':       r['lng'],
        'cx':        round(path['cx'], 1),
        'cy':        round(path['cy'], 1),
    })
(APP_CARTO / 'region-paths.json').write_text(
    json.dumps(region_paths_out, ensure_ascii=False, indent=2))
print(f"✓ region-paths.json ({len(region_paths_out)} régions → app/cartographie/)")

print("\nAll done.")
print("\n── Sources originales (ne jamais supprimer) ────────────────")
print(f"  {DATA / 'Regions_of_Madagascar.svg'}")
print(f"  {DATA / 'madagascar_regions_enriched.csv'}")
print(f"  {DATA / 'build_maps.py'}")
print("\n── Fichiers générés (reproductibles via build_maps.py) ─────")
print(f"  {DATA / 'madagascar-numbered.svg'}")
print(f"  {DATA / 'madagascar-named.svg'}")
print(f"  {DATA / 'madagascar-regions-24.geojson'}")
print(f"  {APP_CARTO / 'region-paths.json'}")
