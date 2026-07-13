import os
import pandas as pd
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors
import xml.etree.ElementTree as ET


cmap = cm.get_cmap('viridis')

NET_FILE = "odessa_peak_static/net/odessa_static_reduced_yellow.net.xml"
POPULATION = 1_010_537  # Luxembourg population (2025)
output_folder = "output"
CO2 = "CO2_abs.csv"
CO = "CO_abs.csv"
HC = "HC_abs.csv"
NOx = "NOx_abs.csv"
PMx = "PMx_abs.csv"


def load_edges(net_file):
    tree = ET.parse(net_file)
    edges = []
    for edge in tree.getroot().findall("edge"):
        edge_id = edge.get("id")
        if edge_id is None or edge_id.startswith(":"):
            continue
        lanes = edge.findall("lane")
        if not lanes:
            continue
        edges.append({
            "id": edge_id,
            "from": edge.get("from"),
            "to": edge.get("to"),
            "type": edge.get("type", "unknown"),
            "length_m": float(lanes[0].get("length", 0)),
            "lane_count": len(lanes),
            "speed_ms": float(lanes[0].get("speed", 0)),
        })
    return edges


def load_junctions(net_file):
    tree = ET.parse(net_file)
    coords = []
    for j in tree.getroot().findall("junction"):
        j_id = j.get("id")
        if j_id is None or j_id.startswith(":"):
            continue
        coords.append((float(j.get("x", 0)), float(j.get("y", 0))))
    return coords


def total_length_km(edges, types=None):
    if types is None:
        return sum(e["length_m"] for e in edges) / 1000
    return sum(e["length_m"] for e in edges if e["type"] in types) / 1000


def estimate_area_km2(net_file):
    tree = ET.parse(net_file)
    loc = tree.getroot().find("location")
    if loc is not None:
        conv = loc.get("convBoundary")
        if conv:
            x_min, y_min, x_max, y_max = [float(v) for v in conv.split(",")]
            area = (x_max - x_min) * (y_max - y_min) / 1e6
            if area > 0:
                return area

    coords = load_junctions(net_file)
    if len(coords) < 2:
        return None
    xs, ys = zip(*coords)
    area = (max(xs) - min(xs)) * (max(ys) - min(ys)) / 1e6
    return area if area > 0 else None


def calculate_emission_metrics(folder_output, net_file, kpis):
    # 1. Calculate Network Metrics
    edges = load_edges(net_file)
    total_length = total_length_km(edges)
    total_area = estimate_area_km2(net_file)

    print(f"=== Network Statistics ===")
    print(f"Total Road Length: {total_length:.2f} km")
    print(f"Total Bounding Area: {total_area:.2f} km²\n")

    results = []

    # 2. Process each KPI
    for kpi in kpis:
        csv_path = os.path.join(folder_output, f"{kpi}_abs.csv")
        if not os.path.exists(csv_path):
            print(f"Warning: {csv_path} not found. Skipping.")
            continue

        # Read the dataframe (time is the index)
        df = pd.read_csv(csv_path, index_col=0)

        # SUMO outputs in mg. sum().sum() gets the total across all edges and timesteps.
        total_mg = df.sum().sum()
        total_g = total_mg / 1000.0  # Convert to grams

        # Calculate densities
        per_km = total_g / total_length if total_length > 0 else 0
        per_km2 = total_g / total_area if (total_area and total_area > 0) else 0

        results.append({
            "KPI": kpi,
            "Total_Emissions_g": round(total_g, 2),
            "Emissions_per_km_g": round(per_km, 2),
            "Emissions_per_km2_g": round(per_km2, 2)
        })

        print(f"--- {kpi} ---")
        print(f"Total:   {total_g:,.2f} g")
        print(f"Per km:  {per_km:,.2f} g/km")
        print(f"Per km²: {per_km2:,.2f} g/km²\n")

    # 3. Save a summary report
    df_results = pd.DataFrame(results)
    summary_path = os.path.join(folder_output, "emissions_density_summary.csv")
    df_results.to_csv(summary_path, index=False)
    print(f"Saved complete summary to: {summary_path}")


def calculate_max_noise(folder_output):
    csv_path = os.path.join(folder_output, "noise.csv")
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found. Ensure noise data was generated.")
        return None

    # Read the noise dataframe
    df = pd.read_csv(csv_path, index_col=0)

    # 1. Find the absolute maximum noise value in the entire DataFrame
    max_noise_val = df.max().max()

    # 2. Find which column (edge_id) contains this maximum value
    max_edge_id = df.max().idxmax()

    # 3. Find which row (time) this maximum value occurred on for that edge
    max_time = df[max_edge_id].idxmax()

    print(f"=== Maximal Noise Level ===")
    print(f"Max Noise: {max_noise_val:.2f} dB")
    print(f"Road Section (Edge ID): {max_edge_id}")
    print(f"Simulation Time: {max_time} s\n")

    return max_noise_val, max_edge_id, max_time

def plot_frame(step, net, kpi, edge_emission, norm, sm, plot_path):
    fig, ax = plt.subplots(figsize=(10, 8))  # Increased width for legend
    for edge in net.getEdges():
        edge_id = edge.getID()
        val = max(1, edge_emission.get(edge_id, 1))

        edge_color = cmap(norm(val))
        shape = edge.getShape()
        x, y = zip(*shape)
        ax.plot(x, y, color=edge_color, linewidth=2)

    ax.set_aspect('equal')
    ax.axis('off')
    if kpi == 'fuel':
        plt.title(f"{kpi} consumption | Simulation second: {step}", fontsize=14)
    else:
        plt.title(f"{kpi} emissions | Simulation second: {step}", fontsize=14)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    if kpi == 'noise':
        cbar.set_label(f"{kpi} emissions [dB]", rotation=270, labelpad=15)
    if kpi == 'fuel':
        cbar.set_label(f"{kpi} consumption [mg]", rotation=270, labelpad=15)
    else:
        cbar.set_label(f"{kpi} emissions [mg]", rotation=270, labelpad=15)
    plt.tight_layout()
    fname = f"{plot_path}/{kpi}_frame_{step}.png"
    plt.savefig(fname, dpi=300)
    plt.close(fig)
    return fname


def plot_gif(net, kpi, path_output, path_plot, snippets):
    frames = []
    fname_list = []
    name = f"{kpi}_emissions.gif"
    if kpi == 'fuel':
        name = f"{kpi}_consumption.gif"

    if os.path.exists(f"{path_output}/{kpi}_abs.csv"):
        df = pd.read_csv(f"{path_output}/{kpi}_abs.csv", index_col=0)
    elif os.path.exists(f"{path_output}/{kpi}.csv"):
        df = pd.read_csv(f"{path_output}/{kpi}.csv", index_col=0)
    else:
        raise FileNotFoundError(f"No CSV file found for {kpi} in {path_output}")

    max_val = df.max().max()
    if kpi == 'noise':
        min_val = 30
        norm = colors.Normalize(vmin=min_val, vmax=max_val)
    else:
        min_val = 1
        norm = colors.LogNorm(vmin=min_val, vmax=max_val)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    for step in df.index:
        edge_emission = df.loc[step].to_dict()
        fname = plot_frame(step, net, kpi, edge_emission, norm, sm, path_plot)
        fname_list.append(fname)
        frames.append(imageio.imread(fname))

    imageio.mimsave(f"{path_plot}/{name}", frames, duration=0.5)
    print(f"Saved {name}!")

    return df


def read_emission(folder_output, kpi, scale=0):
    df = pd.read_csv(f"{folder_output}/{kpi}.csv")
    modifier = 10 ** scale
    df['sum'] = df.sum(axis=1) / modifier / 10000
    total_emission = df.sum(axis=1).sum() / 1000
    print(f"Total {kpi} emission: {total_emission:.2f} g")
    return df


def plot_pollutants(folder_output, aggregate_step=600):
    df_PMx = read_emission(folder_output, 'PMx_abs')
    df_NOx = read_emission(folder_output, 'NOx_abs', 2)
    df_CO = read_emission(folder_output, 'CO_abs', 3)
    df_HC = read_emission(folder_output, 'HC_abs', 1)
    df_CO2 = read_emission(folder_output, 'CO2_abs')
    df_fuel = read_emission(folder_output, 'fuel_abs')

    time = df_PMx.index * 600

    fig, ax = plt.subplots(figsize=(5, 4))
    ax.plot(time, df_PMx['sum'], marker='o', markersize=5, linestyle='-', label='PMx')
    ax.plot(time, df_HC['sum'], marker='o', markersize=5, linestyle='-', label='HC / 10')
    ax.plot(time, df_NOx['sum'], marker='o', markersize=5, linestyle='-', label='NOx / 100')
    ax.plot(time, df_CO['sum'], marker='o', markersize=5, linestyle='-', label='CO / 1000')

    ax.set_xlabel('Time [sec]')
    ax.set_ylabel('Pollutant emissions [g/min]')
    ax.legend()
    ax.grid(True)
    plt.tight_layout()
    plt.savefig(f"{folder_output}/total_PMx_emissions.png", dpi=300)
    plt.show()
    plt.close()


if __name__ == "__main__":
    kpis_to_process = ['CO2', 'CO', 'HC', 'PMx', 'NOx', 'fuel']

    # Run the new calculation
    calculate_emission_metrics(output_folder, NET_FILE, kpis_to_process)
    # 2. Find the maximal noise level on any road section
    calculate_max_noise(output_folder)
