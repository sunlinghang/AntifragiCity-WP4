import os
import sumolib
import xml.etree.ElementTree as ET
from datetime import datetime


aggregate_step = 600
sim_begin = 0
sim_end = 90000  # 25 hours to compensate the final hour
path_plots = "plots"
path_output = "output_dua"
file_config = "dua.static.sumocfg"
dir_scenario = "LuSTScenario-master/scenario"
timestamp = "baseline"
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

sumo_cmd = [
    "sumo",
    "-c", file_new_cfg,
    "--begin", str(sim_begin),
    "--end", str(sim_end),
]
os.system(' '.join(sumo_cmd))
