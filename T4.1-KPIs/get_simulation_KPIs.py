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

KPI_list = []
if get_CO2:
    KPI_list.append('CO2')
if get_CO:
    KPI_list.append('CO')
if get_PMx:
    KPI_list.append('PMx')
if get_NOx:
    KPI_list.append('NOx')
if get_fuel_consumption:
    KPI_list.append('fuel_consumption')
if get_noise_emission:
    KPI_list.append('noise_emission')


aggregate_step = 60
duration = 7200
sumo_binary = "sumo"
conf_file = "LuSTScenario-master/scenario/due.static.sumocfg"
sumo_cmd = [sumo_binary, "-c", conf_file]
net = sumolib.net.readNet('LuSTScenario-master/scenario/lust.net.xml')


traci.start(sumo_cmd)
step = 0
emission_dict = {}
edge_ids = [edge.getID() for edge in net.getEdges()]
edge_emission = {eid: 0 for eid in edge_ids}

while traci.simulation.getMinExpectedNumber() > 0 and step < duration:
    traci.simulationStep()
    step += 1

    for eid in edge_ids:
        edge_emission[eid] += traci.edge.getCO2Emission(eid)

    if step % aggregate_step == 0:
        veh_num = traci.vehicle.getIDCount()
        print(f"Step {step}: {veh_num} vehicles on the road.")
        for eid in edge_ids:
            emission_dict[step] = edge_emission.copy()
        edge_emission = {eid: 0 for eid in edge_ids}

traci.close()

plot_gif(net, emission_dict, name="CO2_emission.gif")

