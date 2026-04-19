import xml.etree.ElementTree as ET

NET_FILE = "LuSTScenario-master/scenario/lust.net.xml"
POPULATION = 681_973 # Luxembourg population (2025)

def load_edges(net_file):
    tree = ET.parse(net_file)
    edges = []
    for edge in tree.getroot().findall("edge"):
        edge_id = edge.get("id")
        if edge_id is None or edge_id.startswith(":"):
            continue
        lanes = edge.findall("lane")
        if not lanes:
            continue
        edges.append({
            "id":        edge_id,
            "from":      edge.get("from"),
            "to":        edge.get("to"),
            "type":      edge.get("type", "unknown"),
            "length_m":  float(lanes[0].get("length", 0)),
            "lane_count": len(lanes),
            "speed_ms":  float(lanes[0].get("speed", 0)),
        })
    return edges

def load_junctions(net_file):
    tree = ET.parse(net_file)
    coords = []
    for j in tree.getroot().findall("junction"):
        j_id = j.get("id")
        if j_id is None or j_id.startswith(":"):
            continue
        coords.append((float(j.get("x", 0)), float(j.get("y", 0))))
    return coords

def estimate_area_km2(net_file):
    tree = ET.parse(net_file)
    loc = tree.getroot().find("location")
    if loc is not None:
        conv = loc.get("convBoundary")
        if conv:
            x_min, y_min, x_max, y_max = [float(v) for v in conv.split(",")]
            area = (x_max - x_min) * (y_max - y_min) / 1e6
            if area > 0:
                return area
 
    coords = load_junctions(net_file)
    if len(coords) < 2:
        return None
    xs, ys = zip(*coords)
    area = (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6
    return area if area > 0 else None

HIGHWAY_TYPES = {
    "highway.motorway", "highway.motorway_link",
    "highway.trunk",    "highway.trunk_link",
}
 
URBAN_TYPES = {
    "highway.residential",  "highway.living_street",
    "highway.tertiary",     "highway.tertiary_link",
    "highway.secondary",    "highway.secondary_link",
    "highway.primary",      "highway.primary_link",
    "highway.unclassified",
}

def total_length_km(edges, types=None):
    if types is None:
        return sum(e["length_m"] for e in edges) / 1000
    return sum(e["length_m"] for e in edges if e["type"] in types) / 1000

def kpi_total_road_length(edges):
    return total_length_km(edges)

def kpi_operating_road_length(edges, exclude_types=None, exclude_ids=None):
    exclude_types = set(exclude_types) if exclude_types else set()
    exclude_ids   = set(exclude_ids)   if exclude_ids   else set()
    return sum(
        e["length_m"] for e in edges
        if e["type"] not in exclude_types and e["id"] not in exclude_ids
    ) / 1000

def kpi_road_standard_ratio(edges):
    total = total_length_km(edges)
    if total == 0:
        return {}
    groups = {}
    for e in edges:
        groups.setdefault(e["type"], 0)
        groups[e["type"]] += e["length_m"]
    return {t: {"length_km": m / 1000, "ratio": m / 1000 / total} for t, m in groups.items()}

def kpi_network_density(edges, area_km2):
    return total_length_km(edges) / area_km2 if area_km2 else None
 
def kpi_highway_density(edges, area_km2):
    return total_length_km(edges, HIGHWAY_TYPES) / area_km2 if area_km2 else None
 
def kpi_urban_road_density(edges, area_km2):
    return total_length_km(edges, URBAN_TYPES) / area_km2 if area_km2 else None
 
def kpi_highway_per_capita(edges, population):
    return total_length_km(edges, HIGHWAY_TYPES) / population if population else None
 
def kpi_urban_per_capita(edges, population):
    return total_length_km(edges, URBAN_TYPES) / population if population else None

def print_section(title):
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")

def print_ratios(ratios, top_n=15):
    for rank, (label, info) in enumerate(
        sorted(ratios.items(), key=lambda x: x[1]["ratio"], reverse=True)[:top_n], 1
    ):
        print(f"  {rank:>2}. {label:<35} {info['length_km']:>8.2f} km   ({info['ratio'] * 100:>5.1f}%)")

if __name__ == "__main__":
    edges   = load_edges(NET_FILE)
    area    = estimate_area_km2(NET_FILE)
 
    print(f"Edges loaded : {len(edges)}")
    print(f"Area         : {area:.4f} km²" if area else "Area: could not be estimated")
 
    print_section("KPI 1 – Total Road Length")
    print(f"  {kpi_total_road_length(edges):.2f} km")
 
    print_section("KPI 2 – Operating Road Length")
    print(f"  {kpi_operating_road_length(edges, exclude_ids={'--30306#4', '--30306#5', '--30306#6'}):.2f} km") # example
 
    print_section("KPI 3 – Road Standard Ratio")
    print_ratios(kpi_road_standard_ratio(edges))
 
    print_section("KPI 4 – Network Density")
    v = kpi_network_density(edges, area)
    print(f"  {v:.4f} km/km²" if v else "  unavailable")
 
    print_section("KPI 5 – Highway Density")
    v = kpi_highway_density(edges, area)
    print(f"  {v:.4f} km/km²" if v else "  unavailable")
 
    print_section("KPI 6 – Urban Road Density")
    v = kpi_urban_road_density(edges, area)
    print(f"  {v:.4f} km/km²" if v else "  unavailable")
 
    print_section("KPI 7 – Highway Length per Capita")
    v = kpi_highway_per_capita(edges, POPULATION)
    print(f"  {v:.6f} km/person  ({v * 1000:.4f} m/person)" if v else "  unavailable")
 
    print_section("KPI 8 – Urban Road Length per Capita")
    v = kpi_urban_per_capita(edges, POPULATION)
    print(f"  {v:.6f} km/person  ({v * 1000:.4f} m/person)" if v else "  unavailable")