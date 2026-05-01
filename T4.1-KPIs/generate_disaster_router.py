import sumolib

NET_FILE = "LuSTScenario-master/scenario/lust.net.xml"

DISASTER_EDGES = [
    "-30620",
    "--30620",
    "-30528#7",
    "--30528#7",
    "--30256#0",
    "-30256#0",
]

BEGIN = 0
END = 21600
OUTPUT_FILE = "LuSTScenario-master/scenario/disaster_closures.add.xml"


def upstream_edges_for_closures(net, closed_edge_ids):
    upstream = set()

    for eid in closed_edge_ids:
        edge = net.getEdge(eid)

        for incoming in edge.getIncoming():
            incoming_id = incoming.getID()

            if incoming_id not in closed_edge_ids:
                upstream.add(incoming_id)

    return sorted(upstream)


def write_rerouter(net_file, closed_edge_ids, output_file):
    net = sumolib.net.readNet(net_file)

    existing = {e.getID() for e in net.getEdges()}
    missing = sorted(set(closed_edge_ids) - existing)

    if missing:
        print("WARNING: These disaster edges were not found in the network:")
        for eid in missing:
            print(f"  - {eid}")

    closed_edge_ids = [eid for eid in closed_edge_ids if eid in existing]
    upstream = upstream_edges_for_closures(net, closed_edge_ids)

    if not upstream:
        raise RuntimeError("No upstream rerouter edges found. Check disaster edge IDs.")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("<additional>\n")
        f.write(
            f'    <rerouter id="disaster_rerouter" '
            f'edges="{" ".join(upstream)}" probability="1">\n'
        )
        f.write(f'        <interval begin="{BEGIN}" end="{END}">\n')

        for eid in closed_edge_ids:
            f.write(f'            <closingReroute id="{eid}" disallow="all"/>\n')

        f.write("        </interval>\n")
        f.write("    </rerouter>\n")
        f.write("</additional>\n")

    print(f"Wrote {output_file}")
    print(f"Closed edges: {len(closed_edge_ids)}")
    print(f"Rerouter trigger edges: {len(upstream)}")

    print("\nRerouter trigger edges:")
    for eid in upstream:
        print(f"  - {eid}")


if __name__ == "__main__":
    write_rerouter(NET_FILE, DISASTER_EDGES, OUTPUT_FILE)