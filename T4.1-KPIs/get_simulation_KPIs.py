import sys
import traci
import sumolib
import argparse
from plotting import plot_gif


get_CO2 = True
get_CO = True
get_PMx = True
get_NOx = True
get_fuel_consumption = True
get_noise_emission = True

kpi_list = []
if get_CO2:
    kpi_list.append('CO2')
if get_CO:
    kpi_list.append('CO')
if get_PMx:
    kpi_list.append('PMx')
if get_NOx:
    kpi_list.append('NOx')
if get_fuel_consumption:
    kpi_list.append('fuel_consumption')
if get_noise_emission:
    kpi_list.append('noise_emission')


aggregate_step = 60
duration = 180
sumo_binary = "sumo"
conf_file = "LuSTScenario-master/scenario/due.static.sumocfg"
sumo_cmd = [sumo_binary, "-c", conf_file]
net = sumolib.net.readNet('LuSTScenario-master/scenario/lust.net.xml')
plot_path = "plots"


traci.start(sumo_cmd)
step = 0
emission_dict = {kpi: {} for kpi in kpi_list}
edge_ids = [edge.getID() for edge in net.getEdges()]
edge_emission = {kpi: {eid: 0.0 for eid in edge_ids} for kpi in kpi_list}

while step < duration:
    traci.simulationStep()
    step += 1

    for eid in edge_ids:
        for kpi in kpi_list:
            if kpi == "CO2":
                func_name = "getCO2Emission"
            elif kpi == "CO":
                func_name = "getCOEmission"
            elif kpi == "PMx":
                func_name = "getPMxEmission"
            elif kpi == "NOx":
                func_name = "getNOxEmission"
            elif kpi == "fuel_consumption":
                func_name = "getFuelConsumption"
            elif kpi == "noise_emission":
                func_name = "getNoiseEmission"
            else:
                continue
            val = getattr(traci.edge, func_name)(eid)
            edge_emission[kpi][eid] += val

    if step % aggregate_step == 0:
        print(f"Step {step}: {traci.vehicle.getIDCount()} vehicles.")

        for kpi in kpi_list:
            emission_dict[kpi][step] = edge_emission[kpi].copy()
            edge_emission[kpi] = {eid: 0.0 for eid in edge_ids}

traci.close()

for kpi in kpi_list:
    plot_gif(net, emission_dict[kpi], name=f"{kpi}_emission.gif", plot_path=plot_path)

