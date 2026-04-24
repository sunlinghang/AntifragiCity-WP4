import os
import pandas as pd
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors


cmap = cm.get_cmap('viridis')


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
        plt.title(f"{kpi} emission | Simulation second: {step}", fontsize=14)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    if kpi == 'noise':
        cbar.set_label(f"{kpi} emission [dB]", rotation=270, labelpad=15)
    if kpi == 'fuel':
        cbar.set_label(f"{kpi} consumption [mg]", rotation=270, labelpad=15)
    else:
        cbar.set_label(f"{kpi} emission [mg]", rotation=270, labelpad=15)
    plt.tight_layout()
    fname = f"{plot_path}/{kpi}_frame_{step}.png"
    plt.savefig(fname, dpi=300)
    plt.close(fig)
    return fname


def plot_gif(net, kpi, path_output, path_plot):
    frames = []
    fname_list = []
    name = f"{kpi}_emission.gif"
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
