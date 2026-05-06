import os
import math
import time
import random
import logging
import statistics
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, Optional, List

import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import sumolib

from get_capacity_KPIs import build_graph, NET_FILE


# ---------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------

BASELINE_TRIPINFO = "LuSTScenario-master/scenario/outputs/baseline.tripinfo.xml"
DISASTER_TRIPINFO = "LuSTScenario-master/scenario/outputs/disaster.tripinfo.xml"

DISASTER_EDGES = [
    "-30620",
    "--30620",
    "-30528#7",
    "--30528#7",
    "--30256#0",
]

OUTPUT_DIR = "plots"

GRAPH_SAMPLE_SIZE = 2000
RANDOM_SEED = 42


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

logger = logging.getLogger(__name__)


def timer_start(message: str):
    logger.info(message)
    return time.time()


def timer_end(start_time: float, message: str):
    elapsed = time.time() - start_time
    logger.info(f"{message} finished in {elapsed:.2f} seconds")


def progress_bar(current: int, total: int, width: int = 40):
    if total <= 0:
        return

    ratio = current / total
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)

    print(
        f"\r[{bar}] {current}/{total} ({100 * ratio:.1f}%)",
        end="",
        flush=True,
    )

    if current == total:
        print()


# ---------------------------------------------------------------------
# Tripinfo parsing
# ---------------------------------------------------------------------

@dataclass
class TripRecord:
    vehicle_id: str
    depart: Optional[float]
    arrival: Optional[float]
    duration: Optional[float]
    route_length: Optional[float]
    waiting_time: Optional[float]
    time_loss: Optional[float]
    depart_delay: Optional[float]
    reroute_no: Optional[int]
    vaporized: bool


def as_float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def as_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def parse_tripinfo(tripinfo_file: str) -> Dict[str, TripRecord]:
    if not os.path.exists(tripinfo_file):
        raise FileNotFoundError(f"Tripinfo file not found: {tripinfo_file}")

    start = timer_start(f"Reading tripinfo file: {tripinfo_file}")

    trips: Dict[str, TripRecord] = {}

    for event, elem in ET.iterparse(tripinfo_file, events=("end",)):
        if elem.tag != "tripinfo":
            continue

        vehicle_id = elem.get("id")
        if vehicle_id is None:
            elem.clear()
            continue

        trips[vehicle_id] = TripRecord(
            vehicle_id=vehicle_id,
            depart=as_float(elem.get("depart")),
            arrival=as_float(elem.get("arrival")),
            duration=as_float(elem.get("duration")),
            route_length=as_float(elem.get("routeLength")),
            waiting_time=as_float(elem.get("waitingTime")),
            time_loss=as_float(elem.get("timeLoss")),
            depart_delay=as_float(elem.get("departDelay")),
            reroute_no=as_int(elem.get("rerouteNo")),
            vaporized=elem.get("vaporized", "false").lower() == "true",
        )

        elem.clear()

        if len(trips) % 100000 == 0:
            logger.info(f"Parsed {len(trips):,} tripinfo records from {tripinfo_file}")

    timer_end(start, f"Loaded {len(trips):,} records from {tripinfo_file}")
    return trips


# ---------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------

def completed_vehicle_ids(trips: Dict[str, TripRecord]) -> set:
    return {
        vehicle_id
        for vehicle_id, trip in trips.items()
        if trip.arrival is not None and not trip.vaporized
    }


def unfinished_vehicle_ids(trips: Dict[str, TripRecord]) -> set:
    return {
        vehicle_id
        for vehicle_id, trip in trips.items()
        if trip.arrival is None and not trip.vaporized
    }


def vaporized_vehicle_ids(trips: Dict[str, TripRecord]) -> set:
    return {
        vehicle_id
        for vehicle_id, trip in trips.items()
        if trip.vaporized
    }


def get_values(
    trips: Dict[str, TripRecord],
    vehicle_ids: set,
    attribute: str,
) -> List[float]:
    output = []

    for vehicle_id in vehicle_ids:
        value = getattr(trips[vehicle_id], attribute)
        if value is not None:
            output.append(float(value))

    return output


def mean_or_none(values: List[float]) -> Optional[float]:
    return statistics.mean(values) if values else None


def median_or_none(values: List[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def percentile_or_none(values: List[float], percentile: float) -> Optional[float]:
    if not values:
        return None

    values = sorted(values)

    if len(values) == 1:
        return values[0]

    k = (len(values) - 1) * percentile
    lower = math.floor(k)
    upper = math.ceil(k)

    if lower == upper:
        return values[int(k)]

    return values[lower] + (values[upper] - values[lower]) * (k - lower)


def ratio_or_none(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def summarize_run(trips: Dict[str, TripRecord]) -> dict:
    completed = completed_vehicle_ids(trips)
    unfinished = unfinished_vehicle_ids(trips)
    vaporized = vaporized_vehicle_ids(trips)

    durations = get_values(trips, completed, "duration")
    route_lengths = get_values(trips, completed, "route_length")
    waiting_times = get_values(trips, completed, "waiting_time")
    time_losses = get_values(trips, completed, "time_loss")
    depart_delays = get_values(trips, completed, "depart_delay")
    reroute_numbers = get_values(trips, completed, "reroute_no")

    return {
        "records_written": len(trips),
        "completed": len(completed),
        "unfinished": len(unfinished),
        "vaporized": len(vaporized),

        "mean_duration": mean_or_none(durations),
        "median_duration": median_or_none(durations),
        "p95_duration": percentile_or_none(durations, 0.95),

        "mean_route_length": mean_or_none(route_lengths),
        "mean_waiting_time": mean_or_none(waiting_times),
        "mean_time_loss": mean_or_none(time_losses),
        "mean_depart_delay": mean_or_none(depart_delays),
        "mean_reroute_no": mean_or_none(reroute_numbers),

        "total_duration": sum(durations),
        "total_waiting_time": sum(waiting_times),
        "total_time_loss": sum(time_losses),
    }


def compare_baseline_and_disaster(
    baseline_trips: Dict[str, TripRecord],
    disaster_trips: Dict[str, TripRecord],
) -> dict:
    start = timer_start("Comparing baseline and disaster tripinfos")

    baseline_completed = completed_vehicle_ids(baseline_trips)
    disaster_completed = completed_vehicle_ids(disaster_trips)

    baseline_ids = set(baseline_trips)
    disaster_ids = set(disaster_trips)

    completed_in_both = baseline_completed & disaster_completed

    duration_deltas = []
    waiting_time_deltas = []
    time_loss_deltas = []
    route_length_deltas = []

    completed_list = list(completed_in_both)
    total = len(completed_list)

    logger.info(f"Computing deltas for {total:,} vehicles completed in both runs")

    for i, vehicle_id in enumerate(completed_list, start=1):
        b = baseline_trips[vehicle_id]
        d = disaster_trips[vehicle_id]

        if b.duration is not None and d.duration is not None:
            duration_deltas.append(d.duration - b.duration)

        if b.waiting_time is not None and d.waiting_time is not None:
            waiting_time_deltas.append(d.waiting_time - b.waiting_time)

        if b.time_loss is not None and d.time_loss is not None:
            time_loss_deltas.append(d.time_loss - b.time_loss)

        if b.route_length is not None and d.route_length is not None:
            route_length_deltas.append(d.route_length - b.route_length)

        if i % 10000 == 0 or i == total:
            progress_bar(i, total)

    baseline_summary = summarize_run(baseline_trips)
    disaster_summary = summarize_run(disaster_trips)

    demand_served = (
        len(completed_in_both) / len(baseline_completed)
        if baseline_completed else 0.0
    )

    result = {
        "baseline": baseline_summary,
        "disaster": disaster_summary,

        "baseline_vehicle_ids": len(baseline_ids),
        "disaster_vehicle_ids": len(disaster_ids),
        "common_vehicle_ids": len(baseline_ids & disaster_ids),
        "missing_from_disaster_tripinfo": len(baseline_ids - disaster_ids),

        "baseline_completed": len(baseline_completed),
        "disaster_completed": len(disaster_completed),
        "completed_in_both": len(completed_in_both),

        "demand_served": demand_served,

        "mean_duration_delta": mean_or_none(duration_deltas),
        "median_duration_delta": median_or_none(duration_deltas),
        "p95_duration_delta": percentile_or_none(duration_deltas, 0.95),

        "mean_waiting_time_delta": mean_or_none(waiting_time_deltas),
        "mean_time_loss_delta": mean_or_none(time_loss_deltas),
        "mean_route_length_delta": mean_or_none(route_length_deltas),

        "duration_ratio": ratio_or_none(
            disaster_summary["mean_duration"],
            baseline_summary["mean_duration"],
        ),
        "waiting_time_ratio": ratio_or_none(
            disaster_summary["mean_waiting_time"],
            baseline_summary["mean_waiting_time"],
        ),
        "time_loss_ratio": ratio_or_none(
            disaster_summary["mean_time_loss"],
            baseline_summary["mean_time_loss"],
        ),
    }

    timer_end(start, "Tripinfo comparison")
    return result


# ---------------------------------------------------------------------
# Graph calculations
# ---------------------------------------------------------------------

def create_damaged_graph(G: nx.Graph, disaster_edges: List[str]) -> nx.Graph:
    start = timer_start("Creating damaged graph")

    G_damaged = G.copy()
    disaster_set = set(disaster_edges)

    removed = 0

    for u, v, data in list(G_damaged.edges(data=True)):
        if data.get("edge_id") in disaster_set:
            G_damaged.remove_edge(u, v)
            removed += 1

    logger.info(f"Removed {removed} graph edges for disaster scenario")
    timer_end(start, "Damaged graph creation")

    return G_damaged


def sampled_graph_connectivity_fraction(
    G: nx.Graph,
    disaster_edges: List[str],
    sample_size: int = 2000,
    seed: int = 42,
) -> float:
    start = timer_start(f"Computing sampled graph connectivity with {sample_size:,} OD pairs")

    random.seed(seed)

    G_damaged = create_damaged_graph(G, disaster_edges)
    nodes = list(G_damaged.nodes())

    if len(nodes) < 2:
        return 1.0

    reachable = 0
    valid = 0

    for i in range(1, sample_size + 1):
        origin = random.choice(nodes)
        destination = random.choice(nodes)

        if origin == destination:
            continue

        valid += 1

        if nx.has_path(G_damaged, origin, destination):
            reachable += 1

        if i % 100 == 0 or i == sample_size:
            progress_bar(i, sample_size)

    fraction = reachable / valid if valid > 0 else 1.0

    logger.info(f"Sampled graph connectivity fraction: {100 * fraction:.2f}%")
    timer_end(start, "Sampled graph connectivity")

    return fraction


def check_disaster_edges_exist(G: nx.Graph, disaster_edges: List[str]) -> None:
    graph_edge_ids = {
        data.get("edge_id")
        for _, _, data in G.edges(data=True)
        if data.get("edge_id")
    }

    missing = sorted(set(disaster_edges) - graph_edge_ids)

    print("\n" + "=" * 60)
    print("DISASTER EDGE CHECK")
    print("=" * 60)
    print(f"Requested disaster edges : {len(disaster_edges)}")
    print(f"Found in graph           : {len(set(disaster_edges) & graph_edge_ids)}")
    print(f"Missing from graph       : {len(missing)}")

    if missing:
        print("\nMissing edge IDs:")
        for edge_id in missing:
            print(f"  - {edge_id}")


# ---------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------

def plot_post_disaster_network(net, disaster_edges: List[str], filename: str) -> None:
    start = timer_start("Plotting post-disaster road closures")

    disaster_set = set(disaster_edges)

    fig, ax = plt.subplots(figsize=(12, 10))

    for edge in net.getEdges():
        edge_id = edge.getID()
        x, y = zip(*edge.getShape())

        if edge_id in disaster_set:
            ax.plot(x, y, color="red", linewidth=2.8, zorder=3)
        else:
            ax.plot(x, y, color="lightgray", linewidth=0.8, zorder=1)

    ax.legend(
        handles=[
            mpatches.Patch(color="lightgray", label="Operational / physical road"),
            mpatches.Patch(color="red", label="Closed road segment"),
        ],
        loc="lower left",
        fontsize=12,
    )

    ax.set_aspect("equal")
    ax.axis("off")

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)

    timer_end(start, f"Saved {filename}")


def plot_metric_comparison(comparison: dict, filename: str) -> None:
    start = timer_start("Plotting baseline vs post-disaster metrics")

    metrics = [
        ("mean_duration", "Mean duration [s]"),
        ("mean_waiting_time", "Mean waiting time [s]"),
        ("mean_time_loss", "Mean time loss [s]"),
        ("mean_route_length", "Mean route length [m]"),
        ("mean_reroute_no", "Mean reroutes"),
    ]

    labels = []
    baseline_values = []
    disaster_values = []

    for key, label in metrics:
        baseline_value = comparison["baseline"].get(key)
        disaster_value = comparison["disaster"].get(key)

        if baseline_value is not None and disaster_value is not None:
            labels.append(label)
            baseline_values.append(baseline_value)
            disaster_values.append(disaster_value)

    if not labels:
        logger.warning("No comparable metrics available for plotting.")
        return

    x = range(len(labels))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.bar([i - width / 2 for i in x], baseline_values, width, label="Baseline")
    ax.bar([i + width / 2 for i in x], disaster_values, width, label="Post-disaster")

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title("Baseline vs Post-Disaster Metrics")
    ax.legend()

    plt.tight_layout()
    plt.savefig(filename, dpi=300)
    plt.close(fig)

    timer_end(start, f"Saved {filename}")


# ---------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------

def fmt(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{100 * value:.2f}%"


def print_post_disaster_report(comparison: dict, graph_fraction: float) -> None:
    print("\n" + "=" * 70)
    print("POST-DISASTER KPI REPORT")
    print("=" * 70)

    print("\nDemand served")
    print("-" * 70)
    print(f"Baseline completed vehicles      : {comparison['baseline_completed']:,}")
    print(f"Post-disaster completed vehicles : {comparison['disaster_completed']:,}")
    print(f"Completed in both runs           : {comparison['completed_in_both']:,}")
    print(f"Demand served                    : {pct(comparison['demand_served'])}")

    print("\nTripinfo record comparison")
    print("-" * 70)
    print(f"Baseline tripinfo records        : {comparison['baseline_vehicle_ids']:,}")
    print(f"Post-disaster tripinfo records   : {comparison['disaster_vehicle_ids']:,}")
    print(f"Common vehicle IDs               : {comparison['common_vehicle_ids']:,}")
    print(f"Missing from disaster tripinfo   : {comparison['missing_from_disaster_tripinfo']:,}")

    print("\nPerformance degradation")
    print("-" * 70)
    print(f"Baseline mean duration           : {fmt(comparison['baseline']['mean_duration'])} s")
    print(f"Disaster mean duration           : {fmt(comparison['disaster']['mean_duration'])} s")
    print(f"Duration ratio                   : {fmt(comparison['duration_ratio'], 3)}x")
    print(f"Mean duration delta              : {fmt(comparison['mean_duration_delta'])} s")
    print(f"Median duration delta            : {fmt(comparison['median_duration_delta'])} s")
    print(f"P95 duration delta               : {fmt(comparison['p95_duration_delta'])} s")

    print(f"\nBaseline mean waiting time       : {fmt(comparison['baseline']['mean_waiting_time'])} s")
    print(f"Disaster mean waiting time       : {fmt(comparison['disaster']['mean_waiting_time'])} s")
    print(f"Waiting time ratio               : {fmt(comparison['waiting_time_ratio'], 3)}x")
    print(f"Mean waiting time delta          : {fmt(comparison['mean_waiting_time_delta'])} s")

    print(f"\nBaseline mean time loss          : {fmt(comparison['baseline']['mean_time_loss'])} s")
    print(f"Disaster mean time loss          : {fmt(comparison['disaster']['mean_time_loss'])} s")
    print(f"Time loss ratio                  : {fmt(comparison['time_loss_ratio'], 3)}x")
    print(f"Mean time loss delta             : {fmt(comparison['mean_time_loss_delta'])} s")

    print(f"\nMean route length delta          : {fmt(comparison['mean_route_length_delta'])} m")

    print("\nUnfinished / vaporized vehicles")
    print("-" * 70)
    print(f"Baseline unfinished              : {comparison['baseline']['unfinished']:,}")
    print(f"Post-disaster unfinished         : {comparison['disaster']['unfinished']:,}")
    print(f"Baseline vaporized               : {comparison['baseline']['vaporized']:,}")
    print(f"Post-disaster vaporized          : {comparison['disaster']['vaporized']:,}")

    print("\nGraph-only post-disaster proxy")
    print("-" * 70)
    print(f"Sampled reachable node fraction  : {pct(graph_fraction)}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

if __name__ == "__main__":
    total_start = timer_start("Starting post-disaster KPI calculation")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    start = timer_start("Loading SUMO network and NetworkX graph")
    net = sumolib.net.readNet(NET_FILE)
    G = build_graph(NET_FILE)
    timer_end(start, "Network loading")

    logger.info(f"NetworkX graph has {G.number_of_nodes():,} nodes and {G.number_of_edges():,} edges")

    check_disaster_edges_exist(G, DISASTER_EDGES)

    baseline_trips = parse_tripinfo(BASELINE_TRIPINFO)
    disaster_trips = parse_tripinfo(DISASTER_TRIPINFO)

    comparison = compare_baseline_and_disaster(
        baseline_trips,
        disaster_trips,
    )

    graph_fraction = sampled_graph_connectivity_fraction(
        G,
        DISASTER_EDGES,
        sample_size=GRAPH_SAMPLE_SIZE,
        seed=RANDOM_SEED,
    )

    print_post_disaster_report(
        comparison,
        graph_fraction,
    )

    plot_post_disaster_network(
        net,
        DISASTER_EDGES,
        f"{OUTPUT_DIR}/post_disaster_closed_edges.png",
    )

    plot_metric_comparison(
        comparison,
        f"{OUTPUT_DIR}/post_disaster_metric_comparison.png",
    )

    timer_end(total_start, "Entire post-disaster KPI calculation")