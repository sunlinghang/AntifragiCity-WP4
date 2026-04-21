import os
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import sumolib
from get_infrastructure_KPIs import estimate_area_km2, kpi_total_road_length, load_edges

NET_FILE   = "VMOD.net.xml"
OUTPUT_DIR = "plots"


def load_bus_edges(net_file):
    tree = ET.parse(net_file)
    root = tree.getroot()
    bus_edges           = []
    exclusive_bus_edges = []

    for edge in root.findall("edge"):
        edge_id = edge.get("id")
        if edge_id is None or edge_id.startswith(":"):
            continue
        lanes = edge.findall("lane")
        if not lanes:
            continue
        length_m      = float(lanes[0].get("length", 0))
        bus_allowed   = False
        bus_exclusive = False

        for lane in lanes:
            allow           = lane.get("allow", "")
            disallow        = lane.get("disallow", "")
            lane_allowed    = set(allow.split())    if allow    else set()
            lane_disallowed = set(disallow.split()) if disallow else set()

            lane_bus_allowed = (
                "bus" in lane_allowed or
                ("all" in lane_allowed and "bus" not in lane_disallowed) or
                (not lane_allowed and "bus" not in lane_disallowed)
            )
            if lane_bus_allowed:
                bus_allowed = True
            if lane_allowed == {"bus"}:
                bus_exclusive = True

        if bus_allowed:
            bus_edges.append({"id": edge_id, "length_m": length_m})
        if bus_exclusive:
            exclusive_bus_edges.append({"id": edge_id, "length_m": length_m})

    return bus_edges, exclusive_bus_edges


def total_km(edges):
    return sum(e["length_m"] for e in edges) / 1000


def plot_bus_routes(net, bus_edges, exclusive_bus_edges, filename):
    bus_ids       = {e["id"] for e in bus_edges}
    exclusive_ids = {e["id"] for e in exclusive_bus_edges}

    fig, ax = plt.subplots(figsize=(12, 10))

    for edge in net.getEdges():
        eid  = edge.getID()
        x, y = zip(*edge.getShape())

        if eid in exclusive_ids:
            ax.plot(x, y, color="red",       linewidth=2.0, zorder=3)
        elif eid in bus_ids:
            ax.plot(x, y, color="blue",      linewidth=1.5, zorder=2)
        else:
            ax.plot(x, y, color="lightgray", linewidth=0.8, zorder=1)

    legend_patches = [
        mpatches.Patch(color="lightgray", label="Other roads"),
        mpatches.Patch(color="blue",      label="Shared bus routes"),
        mpatches.Patch(color="red",       label="Exclusive bus routes"),
    ]
    ax.legend(handles=legend_patches, loc="lower left", fontsize=12, framealpha=0.9)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.title("Bus Route Coverage", fontsize=14)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    edges                          = load_edges(NET_FILE)
    bus_edges, exclusive_bus_edges = load_bus_edges(NET_FILE)
    area_km2                       = estimate_area_km2(NET_FILE)
    total_road_km                  = kpi_total_road_length(edges)
    bus_km                         = total_km(bus_edges)
    exclusive_km                   = total_km(exclusive_bus_edges)

    print(f"Total road length      : {total_road_km:.2f} km")
    print(f"Total bus route length : {bus_km:.2f} km")
    print(f"Exclusive bus length   : {exclusive_km:.2f} km")

    print("\nExclusive bus routes over total bus routes")
    if bus_km > 0:
        print(f"  {exclusive_km / bus_km * 100:.2f} %")
    else:
        print("  No bus routes found in network")

    print("\nBus route length over total road network")
    if total_road_km > 0:
        print(f"  {bus_km / total_road_km * 100:.2f} %")
    else:
        print("  No roads found in network")

    print("\nBus route length per area")
    if area_km2:
        print(f"  {bus_km / area_km2:.4f} km/km²")
    else:
        print("  Area could not be estimated")

    net = sumolib.net.readNet(NET_FILE)
    plot_bus_routes(net, bus_edges, exclusive_bus_edges, f"{OUTPUT_DIR}/bus_routes_map.png")