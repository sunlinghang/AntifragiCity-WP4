"""
Script to analyze trips between Region A and Region B for travel time reliability
Extracts trips that start in Region A and end in Region B from SUMO tripinfo.xml
"""

import xml.etree.ElementTree as ET
import argparse
from pathlib import Path
import statistics
import matplotlib.pyplot as plt
import numpy as np


def extract_edge_ids(region_file):
    """
    Extract edge IDs from a region file.
    The file contains lines like:
    - edge:--32044#1
    - connection:from-30450#1_0to--30946#2_0
    - junction:-24656

    We only want the 'edge:' entries.
    """
    edge_ids = set()

    with open(region_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('edge:'):
                edge_id = line[5:]  # Remove 'edge:' prefix
                edge_ids.add(edge_id)

    return edge_ids


def extract_edge_from_lane(lane_id):
    """
    Extract edge ID from a lane ID.
    Lane IDs are in format: edge_id_lane_number
    e.g., "--32406#3_0" -> "--32406#3"
    """
    # Find the last underscore and take everything before it
    last_underscore = lane_id.rfind('_')
    if last_underscore != -1:
        return lane_id[:last_underscore]
    else:
        # No underscore found, return as is
        return lane_id


def parse_tripinfo_for_region_trips(tripinfo_file, region_a_edges, region_b_edges):
    """
    Parse tripinfo.xml and extract trips that start in region A and end in region B.

    Args:
        tripinfo_file (str): Path to tripinfo.xml
        region_a_edges (set): Set of edge IDs in region A
        region_b_edges (set): Set of edge IDs in region B

    Returns:
        list: List of trip dictionaries for A->B trips
    """

    tree = ET.parse(tripinfo_file)
    root = tree.getroot()

    a_to_b_trips = []

    for tripinfo in root.findall('tripinfo'):
        depart_lane = tripinfo.get('departLane', '')
        arrival_lane = tripinfo.get('arrivalLane', '')

        # Extract edge IDs from lane IDs
        depart_edge = extract_edge_from_lane(depart_lane)
        arrival_edge = extract_edge_from_lane(arrival_lane)

        # Check if this is an A->B trip
        if depart_edge in region_a_edges and arrival_edge in region_b_edges:
            trip = {
                'id': tripinfo.get('id'),
                'depart': float(tripinfo.get('depart', 0)),
                'arrival': float(tripinfo.get('arrival', 0)),
                'duration': float(tripinfo.get('duration', 0)),  # Total trip time (seconds)
                'routeLength': float(tripinfo.get('routeLength', 0)),  # Distance in meters
                'waitingTime': float(tripinfo.get('waitingTime', 0)),  # Waiting time (seconds)
                'timeLoss': float(tripinfo.get('timeLoss', 0)),  # Delay/timeloss (seconds)
                'departEdge': depart_edge,
                'arrivalEdge': arrival_edge,
                'vType': tripinfo.get('vType', ''),
                'speedFactor': float(tripinfo.get('speedFactor', 1.0)),
            }
            a_to_b_trips.append(trip)

    return a_to_b_trips


def analyze_travel_time_reliability(trips):
    """
    Analyze travel time reliability metrics for the A->B trips.

    Args:
        trips (list): List of trip dictionaries

    Returns:
        dict: Dictionary containing reliability metrics
    """

    if not trips:
        return {
            'num_trips': 0,
            'avg_duration': 0,
            'std_duration': 0,
            'min_duration': 0,
            'max_duration': 0,
            'cv_duration': 0,  # Coefficient of variation
            'avg_speed': 0,
            'avg_waiting_time': 0,
            'avg_time_loss': 0,
            'reliability_buffer': 0,  # 95th percentile - avg
        }

    durations = [trip['duration'] for trip in trips]
    distances = [trip['routeLength'] for trip in trips]
    waiting_times = [trip['waitingTime'] for trip in trips]
    time_losses = [trip['timeLoss'] for trip in trips]

    # Basic statistics
    avg_duration = statistics.mean(durations)
    std_duration = statistics.stdev(durations) if len(durations) > 1 else 0
    min_duration = min(durations)
    max_duration = max(durations)

    # Coefficient of variation (reliability measure)
    cv_duration = std_duration / avg_duration if avg_duration > 0 else 0

    # Average speed (km/h)
    total_distance_km = sum(distances) / 1000
    total_time_hours = sum(durations) / 3600
    avg_speed = total_distance_km / total_time_hours if total_time_hours > 0 else 0

    # Reliability buffer (95th percentile - average)
    sorted_durations = sorted(durations)
    percentile_95_idx = int(0.95 * len(sorted_durations))
    percentile_95 = sorted_durations[min(percentile_95_idx, len(sorted_durations) - 1)]
    reliability_buffer = percentile_95 - avg_duration

    return {
        'num_trips': len(trips),
        'avg_duration': avg_duration,
        'std_duration': std_duration,
        'min_duration': min_duration,
        'max_duration': max_duration,
        'cv_duration': cv_duration,
        'avg_speed': avg_speed,
        'avg_waiting_time': statistics.mean(waiting_times),
        'avg_time_loss': statistics.mean(time_losses),
        'reliability_buffer': reliability_buffer,
        'percentile_95': percentile_95,
        'total_distance_km': total_distance_km,
    }


def print_reliability_analysis(metrics, trips):
    """Print travel time reliability analysis."""

    print("\n" + "="*80)
    print("TRAVEL TIME RELIABILITY ANALYSIS: Region A → Region B")
    print("="*80 + "\n")

    if metrics['num_trips'] == 0:
        print("No trips found between Region A and Region B.")
        return

    print("--- TRIP STATISTICS ---")
    print(f"Number of A→B trips: {metrics['num_trips']}")
    print(f"Total distance traveled: {metrics['total_distance_km']:.2f} km")
    print(f"Average trip distance: {metrics['total_distance_km']/metrics['num_trips']:.2f} km")

    print("\n--- TRAVEL TIME METRICS ---")
    print(f"Average duration: {metrics['avg_duration']/60:.2f} minutes ({metrics['avg_duration']:.1f} seconds)")
    print(f"Standard deviation: {metrics['std_duration']/60:.2f} minutes ({metrics['std_duration']:.1f} seconds)")
    print(f"Minimum duration: {metrics['min_duration']/60:.2f} minutes")
    print(f"Maximum duration: {metrics['max_duration']/60:.2f} minutes")
    print(f"95th percentile: {metrics['percentile_95']/60:.2f} minutes")

    print("\n--- RELIABILITY INDICATORS ---")
    print(f"Coefficient of Variation: {metrics['cv_duration']:.3f}")
    print(f"Reliability Buffer (95th - avg): {metrics['reliability_buffer']/60:.2f} minutes")

    # Interpret reliability
    cv = metrics['cv_duration']
    if cv < 0.1:
        reliability = "Very High"
    elif cv < 0.2:
        reliability = "High"
    elif cv < 0.3:
        reliability = "Moderate"
    elif cv < 0.5:
        reliability = "Low"
    else:
        reliability = "Very Low"

    print(f"Reliability Level: {reliability}")

    print("\n--- PERFORMANCE METRICS ---")
    print(f"Average speed: {metrics['avg_speed']:.2f} km/h")
    print(f"Average waiting time: {metrics['avg_waiting_time']/60:.2f} minutes")
    print(f"Average delay (timeloss): {metrics['avg_time_loss']/60:.2f} minutes")

    # Congestion analysis
    avg_waiting = metrics['avg_waiting_time']
    if avg_waiting < 60:  # < 1 minute
        congestion = "Light"
    elif avg_waiting < 300:  # < 5 minutes
        congestion = "Moderate"
    elif avg_waiting < 600:  # < 10 minutes
        congestion = "Heavy"
    else:
        congestion = "Severe"

    print(f"Congestion Level: {congestion}")


def create_reliability_plot(trips, output_file=None):
    """Create a histogram of trip durations for reliability visualization."""

    if not trips:
        print("No trips to plot.")
        return

    durations_min = [trip['duration'] / 60 for trip in trips]

    plt.figure(figsize=(10, 6))
    plt.hist(durations_min, bins=30, alpha=0.7, edgecolor='black')
    plt.xlabel('Trip Duration (minutes)')
    plt.ylabel('Number of Trips')
    plt.title('Travel Time Distribution: Region A → Region B')
    plt.grid(True, alpha=0.3)

    # Add statistics lines
    avg_duration = statistics.mean(durations_min)
    plt.axvline(avg_duration, color='red', linestyle='--', linewidth=2,
                label=f'Average: {avg_duration:.1f} min')

    sorted_durations = sorted(durations_min)
    percentile_95_idx = int(0.95 * len(sorted_durations))
    percentile_95 = sorted_durations[min(percentile_95_idx, len(sorted_durations) - 1)]
    plt.axvline(percentile_95, color='orange', linestyle='--', linewidth=2,
                label=f'95th percentile: {percentile_95:.1f} min')

    plt.legend()

    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()


def save_trips_to_csv(trips, output_file):
    """Save the A->B trips to a CSV file for further analysis."""

    import csv

    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['id', 'depart', 'arrival', 'duration', 'routeLength',
                     'waitingTime', 'timeLoss', 'departEdge', 'arrivalEdge',
                     'vType', 'speedFactor']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(trips)

    print(f"Trip data saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Analyze travel time reliability for trips from Region A to Region B'
    )
    parser.add_argument(
        '--region_a_file',
        type=str,
        default='T4.1-KPIs/LuSTScenario-master/scenario/regionA.txt',
        help='Path to regionA.txt file'    
    )
    parser.add_argument(
        '--region_b_file',
        type=str,
        default='T4.1-KPIs/LuSTScenario-master/scenario/regionB.txt',
        help='Path to regionB.txt file'
    )
    parser.add_argument(
        '--tripinfo_file',
        type=str,
        default='T4.1-KPIs/LuSTScenario-master/scenario/dua.static.tripinfo.xml',
        help='Path to tripinfo.xml file'
    )
    parser.add_argument(
        '--plot',
        type=str,
        default='reliability_plot.png',
        help='Optional: save reliability plot to file (e.g., reliability_plot.png)'
    )
    parser.add_argument(
        '--csv',
        type=str,
        default=None,
        help='Optional: save trip data to CSV file'
    )

    args = parser.parse_args()

    # Check if files exist
    for file_path in [args.region_a_file, args.region_b_file, args.tripinfo_file]:
        if not Path(file_path).exists():
            print(f"Error: File '{file_path}' not found.")
            exit(1)

    # Extract edge IDs from region files
    print(f"Reading region A edges from {args.region_a_file}")
    region_a_edges = extract_edge_ids(args.region_a_file)
    print(f"Found {len(region_a_edges)} edges in Region A")

    print(f"Reading region B edges from {args.region_b_file}")
    region_b_edges = extract_edge_ids(args.region_b_file)
    print(f"Found {len(region_b_edges)} edges in Region B")

    # Parse tripinfo and find A->B trips
    print(f"Parsing tripinfo file: {args.tripinfo_file}")
    a_to_b_trips = parse_tripinfo_for_region_trips(
        args.tripinfo_file, region_a_edges, region_b_edges
    )

    # Analyze reliability
    metrics = analyze_travel_time_reliability(a_to_b_trips)

    # Print results
    print_reliability_analysis(metrics, a_to_b_trips)

    # Create plot if requested
    if args.plot:
        create_reliability_plot(a_to_b_trips, args.plot)

    # Save to CSV if requested
    if args.csv:
        save_trips_to_csv(a_to_b_trips, args.csv)