import os
import imageio.v2 as imageio
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as colors


cmap = cm.get_cmap('viridis')


def plot_frame(step, net, edge_emission, norm, sm):
    fig, ax = plt.subplots(figsize=(10, 8))  # Increased width for legend
    for edge in net.getEdges():
        edge_id = edge.getID()
        val = edge_emission.get(edge_id, 1e-3)
        if val <= 0:
            val = 1e-3

        edge_color = cmap(norm(val))
        shape = edge.getShape()
        x, y = zip(*shape)
        ax.plot(x, y, color=edge_color, linewidth=2)

    ax.set_aspect('equal')
    ax.axis('off')
    plt.title(f"CO2 Emission | Step: {step}", fontsize=14)
    cbar = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.04)
    cbar.set_label('CO2 Emission (mg/min)', rotation=270, labelpad=15)
    plt.tight_layout()
    fname = f"_frame_{step}.png"
    plt.savefig(fname, dpi=300)
    plt.close(fig)
    return fname


def plot_gif(net, emission_dict, name):
    frames = []
    fname_list = []

    all_vals = [val for inner in emission_dict.values() for val in inner.values() if val > 0]
    max_val = max(all_vals) if all_vals else 1000
    min_val = min(all_vals) if all_vals else 0.1

    norm = colors.LogNorm(vmin=min_val, vmax=max_val)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])

    for step, edge_emission in emission_dict.items():
        fname = plot_frame(step, net, edge_emission, norm, sm)
        fname_list.append(fname)
        frames.append(imageio.imread(fname))

    imageio.mimsave(f"{name}", frames, duration=0.5)
    [os.remove(_) for _ in fname_list]
    print(f"Saved {name}!")

