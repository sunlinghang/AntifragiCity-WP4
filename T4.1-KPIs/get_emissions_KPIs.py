import os
import sumolib
import xml.etree.ElementTree as ET
import pandas as pd
from plotting_emission import plot_gif
from datetime import datetime


get_CO2 = True
get_CO = True
get_PMx = True
get_NOx = True
get_HC = True
get_fuel_consumption = True
get_noise_emissions = True

aggregate_step = 600
sim_begin = 0
sim_end = 1000  # 25 hours to compensate the final hour
path_plots = "plots"
path_output = "output"
file_config = "dua.static.sumocfg"
dir_scenario = "LuSTScenario-master/scenario"
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
path_summary = os.path.join(dir_scenario, timestamp)


def get_emission_df(file_results):
    tree = ET.parse(file_results)
    root = tree.getroot()

    rows = []
    for interval in root.findall('interval'):
        start_time = float(interval.get('begin'))
        for edge in interval.findall('edge'):
            rows.append({
                'time': start_time,
                'edge_id': edge.get('id'),
            })
            for kpi in ['CO', 'CO2', 'HC', 'PMx', 'NOx', 'fuel', 'electricity']:
                rows[-1][f'{kpi}_abs'] = float(edge.get(f'{kpi}_abs'))
                rows[-1][f'{kpi}_normed'] = float(edge.get(f'{kpi}_normed'))
                rows[-1][f'{kpi}_perVeh'] = float(edge.get(f'{kpi}_perVeh'))

    df = pd.DataFrame(rows)
    return df


def get_noise_df(file_results):
    tree = ET.parse(file_results)
    root = tree.getroot()

    rows = []
    for interval in root.findall('interval'):
        start_time = float(interval.get('begin'))
        for edge in interval.findall('edge'):
            rows.append({
                'time': start_time,
                'edge_id': edge.get('id'),
                'noise': float(edge.get('noise')),
                'sampledSeconds': float(edge.get('sampledSeconds')),
                'traveltime': float(edge.get('traveltime')),
            })

    df = pd.DataFrame(rows)
    return df


def get_kpi_df(file_emissions, file_noise, path_output):
    df_emission = get_emission_df(file_emissions)
    df_noise = get_noise_df(file_noise)
    df = pd.merge(df_emission, df_noise, on=['time', 'edge_id'], how='outer').fillna(0)
    df.to_csv(f'{path_output}/kpis.csv', index=False)

    for kpi in ['CO', 'CO2', 'HC', 'PMx', 'NOx', 'fuel', 'electricity']:
        df_metric = df.pivot(index='time', columns='edge_id', values=f'{kpi}_abs').fillna(0)
        df_metric.to_csv(f'{path_output}/{kpi}_abs.csv')
    for kpi in ['noise', 'sampledSeconds', 'traveltime']:
        df_metric = df.pivot(index='time', columns='edge_id', values=kpi).fillna(0)
        df_metric.to_csv(f'{path_output}/{kpi}.csv')


kpi_list = []
if get_CO2:
    kpi_list.append('CO2')
if get_CO:
    kpi_list.append('CO')
if get_PMx:
    kpi_list.append('PMx')
if get_NOx:
    kpi_list.append('NOx')
if get_HC:
    kpi_list.append('HC')
if get_fuel_consumption:
    kpi_list.append('fuel')
if get_noise_emissions:
    kpi_list.append('noise')

for p in [path_plots, path_output, path_summary]:
    if not os.path.exists(p):
        os.makedirs(p)

dir_scenario = "LuSTScenario-master/scenario"
file_net = os.path.join(dir_scenario, "lust.net.xml")
file_sumocfg = os.path.join(dir_scenario, file_config)
file_add = os.path.join(dir_scenario, "environment.add.xml")
file_new_cfg = os.path.join(dir_scenario, f"mod.{file_config}")
net = sumolib.net.readNet(file_net)

new_additional = f"""
    <additional>
        <edgeData 
            id="edge_emissions" 
            type="emissions" 
            period="{aggregate_step}" 
            file="emissions.xml" 
            excludeEmpty="true"/>

        <edgeData 
            id="edge_noise" 
            type="harmonoise" 
            period="{aggregate_step}" 
            file="noise.xml" 
            excludeEmpty="true"/>
    </additional>"""

with open(file_add, "w") as f:
    f.write(new_additional)

tree = ET.parse(file_sumocfg)
root = tree.getroot()
additional = root.find(".//additional-files")

if additional is not None:
    value = additional.get("value")
    new_value = f"{value},environment.add.xml"
    additional.set("value", new_value)
    tree.write(file_new_cfg, encoding="UTF-8", xml_declaration=True)
    print(f"Successfully created {file_new_cfg} with updated files: {new_value}")
else:
    print("Error: Could not find <additional-files> in the config.")


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

file_emissions = f"{dir_scenario}/emissions.xml"
file_noise = f"{dir_scenario}/noise.xml"

get_kpi_df(file_emissions, file_noise, path_output)

for kpi in kpi_list:
    df = plot_gif(net, kpi, path_output, path_plots)
