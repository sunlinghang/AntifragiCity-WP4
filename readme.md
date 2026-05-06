# AntifragiCity — Workpackage 4

Codebase and deliverables for **WP4** of the AntifragiCity project.

The current focus is **T4.1 — Antifragile model for urban mobility**, built on top of the open-source [LuST (Luxembourg SUMO Traffic) scenario](https://sumo.dlr.de/docs/networks/luxembourg.html). KPIs from AntifragiCity Task 2.7 are computed directly from SUMO simulation outputs across six domains:

- network and system performance
- transport infrastructure
- travel characteristics
- transport capacity and resilience
- ecological impacts
- energy consumption

Example visualisation — CO₂ emissions on an average day in the benchmark:

![CO2 emissions](T4.1-KPIs/plots/gif/CO2_emissions.gif)

---

## Repository structure

```
AntifragiCity-WP4/
├── README.md
├── .gitignore
└── T4.1-KPIs/
    ├── LuSTScenario-master/        # SUMO scenario (network, demand, configs)
    │   └── scenario/
    │       ├── lust.net.xml        # road network
    │       ├── dua.static.sumocfg  # baseline SUMO config
    │       ├── disaster.sumocfg    # disaster-scenario SUMO config
    │       └── outputs/            # SUMO outputs (tripinfo, summary, …)
    ├── plots/                      # generated figures and GIFs
    ├── get_infrastructure_KPIs.py  # road-length, density, junction KPIs
    ├── get_capacity_KPIs.py        # graph build + centrality / commuter flow
    ├── get_emissions_KPIs.py       # CO₂, CO, NOx, PMx, HC, fuel, noise
    ├── get_resilience_KPIs.py      # redundancy, entropy, post-disaster maps
    ├── get_capacity_KPIs.py        # capacity / centrality KPIs
    ├── get_lane_closure_KPIs.py    # TraCI-driven lane-closure experiment
    ├── get_and_plot_bus_KPIs.py    # bus-network coverage KPIs
    ├── get_benchmark.py            # prepares the baseline SUMO run
    ├── generate_disaster_router.py # builds the disaster closure additional file
    ├── compare_disaster_KPIs.py    # baseline-vs-disaster comparison
    ├── plotting_capacity.py        # centrality maps
    ├── plotting_emission.py        # emission frame & GIF rendering
    ├── plotting_lane_closure.py    # closure-experiment time series
    └── plotting_road_types.py      # road-type maps and bar charts
```

All scripts are designed to be run from inside the `T4.1-KPIs/` directory: file paths such as `LuSTScenario-master/scenario/lust.net.xml` are resolved relative to that working directory.

---

## Requirements

- **Python** 3.8+ (tested with 3.8 and 3.13)
- **SUMO** ≥ 1.0 (LuST was generated with SUMO 0.26 but runs on modern versions; results are no longer formally validated — see the LuST README)
- The `SUMO_HOME` environment variable must be set so that `sumolib` and `traci` resolve correctly
- Python packages:
  - `sumolib`, `traci` (ship with SUMO)
  - `networkx`
  - `numpy`, `scipy`, `pandas`
  - `matplotlib`
  - `imageio`

Install the Python deps with:

```bash
pip install networkx numpy scipy pandas matplotlib imageio
```

---

## Running the KPI pipeline

All commands below assume you are in `T4.1-KPIs/`:

```bash
cd T4.1-KPIs
```

### 1. Baseline SUMO simulation

`get_benchmark.py` patches the SUMO config to emit `summary`, `tripinfo`, and `edgedata` outputs and runs the baseline `dua.static` scenario.

```bash
python get_benchmark.py
```

Outputs are written to `LuSTScenario-master/scenario/outputs/` (see `.gitignore` — large XML outputs are not committed).

### 2. Infrastructure KPIs

```bash
python get_infrastructure_KPIs.py
```

Reports total road length, road density, and junction statistics from `lust.net.xml`. Used as a library by several plotting modules.

### 3. Capacity / centrality KPIs

```bash
python get_capacity_KPIs.py        # KPI numbers
python plotting_capacity.py        # betweenness / closeness / degree / eigenvector / commuter-flow maps
```

`plotting_capacity.py` requires an `edgedata` output file from a SUMO run (see step 1).

### 4. Emissions and energy KPIs

```bash
python get_emissions_KPIs.py
```

Aggregates CO₂, CO, NOx, PMx, HC, fuel and noise. Renders per-pollutant GIFs into `plots/gif/` via `plotting_emission.py`.

### 5. Bus-network KPIs

```bash
python get_and_plot_bus_KPIs.py
```

Computes bus-route coverage and renders `plots/bus_routes_map.png`.

### 6. Road-type breakdown

```bash
python plotting_road_types.py
```

Renders `plots/road_type_map.png` and `plots/road_type_bar.png`.

### 7. Lane-closure experiment

```bash
python get_lane_closure_KPIs.py
python plotting_lane_closure.py
```

Runs a TraCI-driven simulation that closes a configurable percentage of lanes for one hour starting at 08:00 and plots the resulting vehicle-count time series.

### 8. Disaster scenario and resilience

```bash
python generate_disaster_router.py   # writes disaster_closures.add.xml
sumo -c LuSTScenario-master/scenario/disaster.sumocfg
python get_resilience_KPIs.py        # redundancy, entropy, post-disaster maps
python compare_disaster_KPIs.py      # baseline vs. disaster comparison
```

`compare_disaster_KPIs.py` expects both `baseline.tripinfo.xml` and `disaster.tripinfo.xml` in `LuSTScenario-master/scenario/outputs/`.

---

## Outputs

- Static figures: `T4.1-KPIs/plots/*.png`
- Animated KPIs: `T4.1-KPIs/plots/gif/*.gif`
- Console KPI summaries are printed by each `get_*_KPIs.py` script.

---

## Module dependency graph

```
get_infrastructure_KPIs.py  ──▶  get_and_plot_bus_KPIs.py
                            ──▶  plotting_road_types.py

get_capacity_KPIs.py        ──▶  plotting_capacity.py
                            ──▶  get_resilience_KPIs.py
                            ──▶  compare_disaster_KPIs.py

plotting_emission.py        ──▶  get_emissions_KPIs.py
```

The flat layout inside `T4.1-KPIs/` is intentional — every script is run from that directory and imports its siblings by module name.

---

## Credits

The SUMO scenario under `T4.1-KPIs/LuSTScenario-master/` is the work of L. Codeca *et al.* and is redistributed under the MIT license. See `T4.1-KPIs/LuSTScenario-master/README.md` and `LICENSE.md` for citation and licensing details.
