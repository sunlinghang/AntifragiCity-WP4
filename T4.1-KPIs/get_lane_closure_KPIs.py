import os
import traci
import random
import sumolib
import xml.etree.ElementTree as ET
from datetime import datetime

SEED = 42
random.seed(SEED)

closed_status = False
closure_pct = 0.01
close_start = 28800
close_period = 3600
close_end = close_start + close_period  # 1 hour closure starting at 7 AM


aggregate_step = 600
sim_begin = 0
sim_end = 90000  # 25 hours to compensate the final hour

path_plots = "plots"
path_output = "output_dua"
file_config = "dua.static.sumocfg"
dir_scenario = "LuSTScenario-master/scenario"
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
timestamp = f"closure_{int(closure_pct*100)}pct_{close_start//3600}h-{close_end//3600}h_{timestamp}"
path_summary = os.path.join(dir_scenario, timestamp)

for p in [path_plots, path_output, path_summary]:
    if not os.path.exists(p):
        os.makedirs(p)

file_net = os.path.join(dir_scenario, "lust.net.xml")
file_sumocfg = os.path.join(dir_scenario, file_config)
file_new_cfg = os.path.join(dir_scenario, f"mod.{file_config}")
net = sumolib.net.readNet(file_net)

tree = ET.parse(file_sumocfg)
root = tree.getroot()
summary = root.find(".//summary-output")
tripinfo = root.find(".//tripinfo-output")
edgedata = root.find(".//edgedata-output")
log = root.find(".//log")

if summary is not None:
    value = summary.get("value")
    new_value = f"{timestamp}/{value}"
    summary.set("value", new_value)
if tripinfo is not None:
    value = tripinfo.get("value")
    new_value = f"{timestamp}/{value}"
    tripinfo.set("value", new_value)
if edgedata is not None:
    value = edgedata.get("value")
    new_value = f"{timestamp}/{value}"
    edgedata.set("value", new_value)
if log is not None:
    value = log.get("value")
    new_value = f"{timestamp}/{value}"
    log.set("value", new_value)

tree.write(file_new_cfg, encoding="UTF-8", xml_declaration=True)


net = sumolib.net.readNet(file_net)
all_edges = [e.getID() for e in net.getEdges() if e.getFunction() == '']
num_to_close = int(len(all_edges) * closure_pct)
edges_to_close = random.sample(all_edges, num_to_close)
print(f"Seed {SEED}: Selected {len(edges_to_close)} edges for closure.")


traci.start([
    "sumo",
    "-c", file_new_cfg,
    "--begin", str(sim_begin),
    "--end", str(sim_end),
    "--ignore-route-errors", "true",          # If a car is TRULY trapped, delete it
])

while traci.simulation.getTime() < sim_end:
    traci.simulationStep()
    curr_time = traci.simulation.getTime()

    if close_start <= curr_time <= close_end:
        if not closed_status:
            for edge_id in edges_to_close:
                traci.edge.setDisallowed(edge_id, ["all"])  # Disallow all vehicle classes
            print(f"Time {curr_time}: Applied {closure_pct}% lane closures.")
            closed_status = True

    elif curr_time > close_end and closed_status:
        for edge_id in edges_to_close:
            traci.edge.setDisallowed(edge_id, [])  # Reset to default
        print(f"Time {curr_time}: Re-opened lanes.")
        closed_status = False

traci.close()
