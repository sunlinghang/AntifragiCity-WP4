import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import sumolib

from get_capacity_KPIs import (
    build_graph,
    load_edgedata,
    compute_betweenness,
    compute_closeness,
    compute_degree,
    eigenvector_centrality,
    compute_commuter_flow,
    NET_FILE,
    EDGEDATA_FILE,
)

cmap = cm.get_cmap("viridis")
output_dir = "plots"

def edge_scores_from_nodes(net, node_scores):
    edge_scores = {}
    for edge in net.getEdges():
        frm = edge.getFromNode().getID()
        to = edge.getToNode().getID()
        edge_scores[edge.getID()] = (node_scores.get(frm, 0) + node_scores.get(to, 0)) / 2
    return edge_scores

def plot_kpi(net, edge_scores, title, filename):
    all_values = list(edge_scores.values())
    vmin, vmax = min(all_values), max(all_values)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    fig, ax = plt.subplots(figsize=(10, 8))

    for edge in net.getEdges():
        val = edge_scores.get(edge.getID(), 0)
        color = cmap(norm(val))
        x, y = zip(*edge.getShape())
        ax.plot(x, y, color=color, linewidth=1.5)
    ax.set_aspect("equal")
    ax.axis("off")
    plt.title(title, fontsize=14)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label("Centrality Score", rotation=270, labelpad=15)
 
    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)
    print(f"Saved {filename}")

if __name__ == "__main__":
    import os
    os.makedirs(output_dir, exist_ok=True)
    net = sumolib.net.readNet(NET_FILE)
    G = build_graph(NET_FILE)

    kpis = {
        "Betweenness Centrality" : compute_betweenness(G),
        "Closeness Centrality"   : compute_closeness(G),
        "Degree Centrality"      : compute_degree(G),
        "Eigenvector Centrality" : eigenvector_centrality(G),
    }

    edge_flows = load_edgedata(EDGEDATA_FILE)
    kpis["Commuter Flow Centrality"] = compute_commuter_flow(G, edge_flows, NET_FILE)

    for title, node_scores in kpis.items():
        edge_scores = edge_scores_from_nodes(net, node_scores)
        filename    = f"{output_dir}/{title.lower().replace(' ', '_')}.png"
        plot_kpi(net, edge_scores, title, filename)