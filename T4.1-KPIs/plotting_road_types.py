import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.cm as cm
import numpy as np
import sumolib

from get_infrastructure_KPIs import load_edges, NET_FILE

OUTPUT_DIR = "plots"

def build_type_colormap(edges):
    types  = sorted(set(e["type"] for e in edges))
    colors = cm.get_cmap("tab20", len(types))
    return {t: colors(i) for i, t in enumerate(types)}

def plot_map(net, edges, type_colors, filename):
    edge_type = {e["id"]: e["type"] for e in edges}

    fig, ax = plt.subplots(figsize=(12, 10))

    for edge in net.getEdges():
        eid   = edge.getID()
        etype = edge_type.get(eid)
        if etype is None:
            continue
        color = type_colors.get(etype, (0.5, 0.5, 0.5, 1.0))
        x, y  = zip(*edge.getShape())
        ax.plot(x, y, color=color, linewidth=1.2)

    legend_patches = [
        mpatches.Patch(color=color, label=t.replace("highway.", ""))
        for t, color in sorted(type_colors.items())
    ]
    ax.legend(
        handles=legend_patches,
        loc="lower left",
        fontsize=12,
        framealpha=0.9,
        ncol=2,
    )

    ax.set_aspect("equal")
    ax.axis("off")
    plt.title("Road Types", fontsize=14)
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")

def plot_bar(edges, type_colors, filename):
    type_lengths = {}
    for e in edges:
        type_lengths[e["type"]] = type_lengths.get(e["type"], 0) + e["length_m"] / 1000

    labels  = sorted(type_lengths.keys())
    values  = [type_lengths[t] for t in labels]
    colors  = [type_colors.get(t, (0.5, 0.5, 0.5)) for t in labels]

    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(range(len(labels)), values, color=colors)
    for bar, value in zip(bars,values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{value:.1f}", ha="center", va="bottom", fontsize=10)

    clean_labels = [t.replace("highway.", "") for t in labels]
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(clean_labels, rotation=45, ha="right", fontsize=14)
    ax.set_ylabel("Length (km)")

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")

if __name__ == "__main__":
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    net         = sumolib.net.readNet(NET_FILE)
    edges       = load_edges(NET_FILE)
    type_colors = build_type_colormap(edges)

    plot_map(net, edges, type_colors, f"{OUTPUT_DIR}/road_type_map.png")
    plot_bar(edges, type_colors,      f"{OUTPUT_DIR}/road_type_bar.png")