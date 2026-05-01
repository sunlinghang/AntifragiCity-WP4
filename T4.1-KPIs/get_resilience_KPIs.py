import os
import math
import random
import xml.etree.ElementTree as ET
from collections import defaultdict

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import sumolib

from get_capacity_KPIs import build_graph, NET_FILE


TRIPINFO_FILE  = "LuSTScenario-master/scenario/dua.static.tripinfo.xml"
DISASTER_EDGES = ["-30620", "--30620", "-30528#7", "--30528#7", "--30256#0", "--30256#0"] # manually picked highly critical edges
OUTPUT_DIR     = "plots"
CMAP           = cm.get_cmap("viridis")


def kpi_redundancy(G):
    edge_betweenness = nx.edge_betweenness_centrality(G, weight="weight", normalized=True)
    active  = sum(1 for v in edge_betweenness.values() if v > 0)
    dormant = sum(1 for v in edge_betweenness.values() if v == 0)
    return {
        "active":           active,
        "dormant":          dormant,
        "ratio":            dormant / active if active > 0 else 0,
        "edge_betweenness": edge_betweenness,
    }


def plot_redundancy(net, G, edge_betweenness, filename):
    edge_id_to_endpoints = {
        data["edge_id"]: (u, v)
        for u, v, data in G.edges(data=True)
        if "edge_id" in data
    }
    endpoints_to_betweenness = {
        (u, v): edge_betweenness.get((u, v), 0)
        for u, v in G.edges()
    }

    all_vals = list(edge_betweenness.values())
    vmax     = max(all_vals) if all_vals else 1
    norm     = mcolors.Normalize(vmin=0, vmax=vmax)
    sm       = plt.cm.ScalarMappable(cmap=CMAP, norm=norm)
    sm.set_array([])

    fig, ax = plt.subplots(figsize=(12, 10))
    for edge in net.getEdges():
        eid       = edge.getID()
        endpoints = edge_id_to_endpoints.get(eid)
        val       = endpoints_to_betweenness.get(endpoints, 0) if endpoints else 0
        color     = CMAP(norm(val))
        x, y      = zip(*edge.getShape())
        ax.plot(x, y, color=color, linewidth=1.5)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.title("Network Redundancy (Edge Betweenness)", fontsize=14)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Edge Betweenness (0 = dormant)", rotation=270, labelpad=15)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")


def load_od_flows(tripinfo_file):
    tree  = ET.parse(tripinfo_file)
    flows = defaultdict(int)
    for trip in tree.getroot().findall("tripinfo"):
        depart_lane = trip.get("departLane", "")
        arrive_lane = trip.get("arrivalLane", "")
        origin      = depart_lane.rsplit("_", 1)[0] if depart_lane else None
        destination = arrive_lane.rsplit("_", 1)[0]  if arrive_lane else None
        if origin and destination:
            flows[(origin, destination)] += 1
    return dict(flows)


def kpi_entropy(od_flows):
    total = sum(od_flows.values())
    if total == 0:
        return 0.0
    entropy     = -sum((c / total) * math.log2(c / total) for c in od_flows.values() if c > 0)
    max_entropy = math.log2(len(od_flows)) if len(od_flows) > 1 else 1
    return entropy / max_entropy


def plot_entropy(net, od_flows, filename):
    edge_flow = defaultdict(int)
    for (origin, destination), count in od_flows.items():
        edge_flow[origin]      += count
        edge_flow[destination] += count

    all_vals = [v for v in edge_flow.values() if v > 0]
    vmin     = min(all_vals) if all_vals else 1
    vmax     = max(all_vals) if all_vals else 1
    norm     = mcolors.LogNorm(vmin=vmin, vmax=vmax)
    sm       = plt.cm.ScalarMappable(cmap=CMAP, norm=norm)
    sm.set_array([])

    fig, ax = plt.subplots(figsize=(12, 10))
    for edge in net.getEdges():
        eid   = edge.getID()
        val   = max(edge_flow.get(eid, 0), vmin)
        color = CMAP(norm(val))
        x, y  = zip(*edge.getShape())
        ax.plot(x, y, color=color, linewidth=1.5)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.title("Network Entropy — OD Flow Concentration per Edge", fontsize=14)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Total OD trips through edge (log scale)", rotation=270, labelpad=15)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")


def kpi_post_disaster_fraction(G, disaster_edges, sample_size=500):
    G_damaged = G.copy()
    for u, v, data in G.edges(data=True):
        if data.get("edge_id") in disaster_edges:
            G_damaged.remove_edge(u, v)

    nodes = list(G.nodes())
    if len(nodes) < 2:
        return 1.0

    pairs     = [(random.choice(nodes), random.choice(nodes)) for _ in range(sample_size)]
    reachable = sum(1 for o, d in pairs if o != d and nx.has_path(G_damaged, o, d))
    valid     = sum(1 for o, d in pairs if o != d)
    return reachable / valid if valid > 0 else 1.0


def plot_post_disaster(net, disaster_edges, filename):
    disaster_set = set(disaster_edges)

    fig, ax = plt.subplots(figsize=(12, 10))
    for edge in net.getEdges():
        eid  = edge.getID()
        x, y = zip(*edge.getShape())
        if eid in disaster_set:
            ax.plot(x, y, color="red",       linewidth=2.5, zorder=3)
        else:
            ax.plot(x, y, color="lightgray", linewidth=0.8, zorder=1)

    ax.legend(handles=[
        mpatches.Patch(color="lightgray", label="Operational"),
        mpatches.Patch(color="red",       label="Removed (disaster)"),
    ], loc="lower left", fontsize=9)

    ax.set_aspect("equal")
    ax.axis("off")
    plt.title("Post-Disaster Network", fontsize=14)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    net = sumolib.net.readNet(NET_FILE)
    G   = build_graph(NET_FILE)
    print(f"Network: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    print("\n" + "=" * 55)
    print("  Network Redundancy Ratio")
    print("=" * 55)
    r = kpi_redundancy(G)
    print(f"  Active edges  : {r['active']}")
    print(f"  Dormant edges : {r['dormant']}")
    print(f"  Ratio         : {r['ratio']:.4f}")
    plot_redundancy(net, G, r["edge_betweenness"], f"{OUTPUT_DIR}/redundancy_map.png")

    print("\n" + "=" * 55)
    print("  Network Entropy of Mobility Flows")
    print("=" * 55)
    try:
        od_flows = load_od_flows(TRIPINFO_FILE)
        entropy  = kpi_entropy(od_flows)
        print(f"  OD pairs      : {len(od_flows)}")
        print(f"  Entropy score : {entropy:.4f}  (0 = concentrated, 1 = uniform)")
        plot_entropy(net, od_flows, f"{OUTPUT_DIR}/entropy_map.png")
    except FileNotFoundError:
        print("  tripinfo file not found — run the simulation first")

    print("\n" + "=" * 55)
    print("  Post-Disaster Demand Fraction")
    print("=" * 55)
    if DISASTER_EDGES:
        fraction = kpi_post_disaster_fraction(G, DISASTER_EDGES)
        print(f"  Edges removed : {len(DISASTER_EDGES)}")
        print(f"  Demand served : {fraction * 100:.2f} %")
        plot_post_disaster(net, DISASTER_EDGES, f"{OUTPUT_DIR}/post_disaster_map.png")
    else:
        print("  No disaster edges defined — add edge IDs to DISASTER_EDGES list")