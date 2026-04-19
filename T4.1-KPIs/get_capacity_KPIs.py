import os
import sys
import xml.etree.ElementTree as ET
import networkx as nx
import sumolib

NET_FILE = "LuSTScenario-master/scenario/lust.net.xml"
EDGEDATA_FILE = "LuSTScenario-master/scenario/lust.edgedata.xml"
TOP_N = 10

def build_graph(net_file):
    net = sumolib.net.readNet(net_file)
    G = nx.DiGraph()
    for node in net.getNodes():
        G.add_node(node.getID())

    for edge in net.getEdges():
        frm = edge.getFromNode().getID()
        to = edge.getToNode().getID()
        length = edge.getLength()
        G.add_edge(frm, to, distance=length, edge_id=edge.getID())
    return G

def load_edgedata(edgedata_file):
    tree = ET.parse(edgedata_file)
    flows = {}
    for interval in tree.getroot().findall("interval"):
        for edge in interval.findall("edge"):
            edge_id = edge.get("id")
            if edge_id and not edge_id.startswith(":"):
                count = float(edge.get("entered") or edge.get("left") or 0)
                flows[edge_id] = flows.get(edge_id, 0) + count
    return flows

def compute_betweenness(G):
    return nx.betweenness_centrality(G, weight="weight")

def compute_closeness(G):
    return nx.closeness_centrality(G, distance="distance")

def compute_degree(G):
    return nx.degree_centrality(G)

def eigenvector_centrality(G):
    scc_nodes = max(nx.strongly_connected_components(G), key=len)
    subgraph = G.subgraph(scc_nodes)
    ev = nx.eigenvector_centrality(subgraph, weight="weight")
    return {node: ev.get(node, 0) for node in G.nodes()}

def compute_commuter_flow(G, edge_flows, net_file):
    net = sumolib.net.readNet(net_file)
    node_flows = {node: 0.0 for node in G.nodes()}
    for edge in net.getEdges():
        edge_id = edge.getID()
        flow = edge_flows.get(edge_id, 0.0)
        frm = edge.getFromNode().getID()
        to = edge.getToNode().getID()
        if frm in node_flows:
            node_flows[frm] += flow
        if to in node_flows:
            node_flows[to] += flow
    max_flow = max(node_flows.values(), default=1) or 1
    return {node: flow / max_flow for node, flow in node_flows.items()}

def print_top(label, scores, top_n=TOP_N):
    print(f"\n{'=' * 55}\n  {label}\n{'=' * 55}")
    for rank, (node, value) in enumerate(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n], 1):
        print(f"{rank:>2}. {node:<20}: {value:.6f}")

if __name__ == "__main__":
    G = build_graph(NET_FILE)
    print_top("Betweenness Centrality", compute_betweenness(G))
    print_top("Closeness Centrality", compute_closeness(G))
    print_top("Degree Centrality", compute_degree(G))
    print_top("Eigenvector Centrality", eigenvector_centrality(G))
    edge_flows = load_edgedata(EDGEDATA_FILE)
    print_top("Commuter Flow", compute_commuter_flow(G, edge_flows, NET_FILE))