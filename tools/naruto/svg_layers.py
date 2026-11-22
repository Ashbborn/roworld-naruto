#!/usr/bin/env python3
"""Make render-ready SVGs from the Narutopedia world map (build/narutosrc/w.svg):
  countries.svg: sea + each land polygon filled with a unique colour (index i -> rgb(i+1, 0, 255-?)), no strokes
  villages.svg:  only the "Village Symbol *" groups, each filled with a unique colour
Usage: python tools/naruto/svg_layers.py <src.svg> <outdir> <width> <height>
"""
import re, sys, json
src, out, W, H = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
s = open(src, encoding="utf8").read()
# scale to W x H
s = re.sub(r'(<svg\b[^>]*?)\swidth="1500"', r'\1 width="%d"' % W, s, count=1, flags=re.S)
s = re.sub(r'(<svg\b[^>]*?)\sheight="882.2204"', r'\1 height="%d" viewBox="0 0 1500 882.2204" preserveAspectRatio="none"' % H, s, count=1, flags=re.S)

land_ids = []
def tag_land(m):
    p = m.group(0)
    if "#a7cc95" in p:
        i = re.search(r'\bid="([^"]*)"', p).group(1)
        land_ids.append(i)
    return p
s_l = re.sub(r'<path\b[^>]*?/>', tag_land, s, flags=re.S)
css = ["*{visibility:hidden;shape-rendering:crispEdges}", "svg{visibility:visible;background:#000}",
       "#rect3552{visibility:visible;fill:#0000ff !important;stroke:none !important}"]
colors = {}
for n, i in enumerate(land_ids, 1):
    colors[i] = n
    css.append("#%s{visibility:visible;fill:rgb(%d,%d,0) !important;stroke:none !important}" % (i, n * 6, 255 - n * 6))
def inject(doc, rules):
    return re.sub(r'(<svg\b[^>]*>)', lambda m: m.group(1) + "<style>" + "".join(rules) + "</style>", doc, count=1, flags=re.S)
open(out + "/countries.svg", "w", encoding="utf8").write(inject(s_l, css))

vids = re.findall(r'id="(Village Symbol [^"]*)"', s)
vcss = ["*{visibility:hidden;shape-rendering:crispEdges}", "svg{visibility:visible;background:#000}"]
s_v = s
vmap = {}
for n, v in enumerate(vids, 1):
    safe = "vs" + str(n)
    s_v = s_v.replace('id="%s"' % v, 'id="%s"' % safe)
    vmap[v.replace("Village Symbol ", "")] = n
    vcss.append("#%s, #%s *{visibility:visible;fill:rgb(%d,255,0) !important;stroke:rgb(%d,255,0) !important}" % (safe, safe, n * 20, n * 20))
open(out + "/villages.svg", "w", encoding="utf8").write(inject(s_v, vcss))
json.dump({"land": colors, "villages": vmap}, open(out + "/layers.json", "w"), indent=1)
print(len(land_ids), "land polys,", len(vids), "villages")
