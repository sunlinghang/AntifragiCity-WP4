"""
Script to extract KPIs from SUMO tripinfo.xml file
Analyzes:
1. Total vehicle kilometers travelled
2. Total travel time
3. Average trip duration per vehicle
4. Average trip duration per kilometer
5. Average bus speed
6. Average bus trip duration
7. Total public transport (bus) distance travelled
8. Total delays (timeloss), average delay per vehicle
9. Congestion level (average waiting time)
"""

import xml.etree.ElementTree as ET
import argparse
from pathlib import Path


def parse_tripinfo(tripinfo_file):
    """
    Parse the tripinfo XML file and extract KPIs.
    
    Args:
        tripinfo_file (str): Path to the tripinfo.xml file
        
    Returns:
        dict: Dictionary containing all calculated KPIs
    """
    
    tree = ET.parse(tripinfo_file)
    root = tree.getroot()
    
    # Initialize containers
    trips = []
    bus_trips = []
    
    # Parse all tripinfo elements
    for tripinfo in root.findall('tripinfo'):
        trip = {
            'id': tripinfo.get('id'),
            'duration': float(tripinfo.get('duration', 0)),  # Total trip time (seconds)
            'routeLength': float(tripinfo.get('routeLength', 0)),  # Distance in meters
            'waitingTime': float(tripinfo.get('waitingTime', 0)),  # Waiting time (seconds)
            'timeLoss': float(tripinfo.get('timeLoss', 0)),  # Delay/timeloss (seconds)
            'vType': tripinfo.get('vType', ''),  # Vehicle type
            'departSpeed': float(tripinfo.get('departSpeed', 0)),
            'arrivalSpeed': float(tripinfo.get('arrivalSpeed', 0)),
        }
        
        trips.append(trip)
        
        # Identify buses (common identifiers in SUMO)
        if 'bus' in trip['id'].lower() or 'bus' in trip['vType'].lower() or trip['vType'].startswith('bus'):
            bus_trips.append(trip)
    
    # Calculate KPIs
    kpis = calculate_kpis(trips, bus_trips)
    
    return kpis, trips, bus_trips


def calculate_kpis(trips, bus_trips):
    """
    Calculate all KPIs from the trip data.
    
    Args:
        trips (list): All trips
        bus_trips (list): Bus trips only
        
    Returns:
        dict: Dictionary of KPIs
    """
    
    kpis = {}
    
    if not trips:
        print("No trips found in the tripinfo file.")
        return kpis
    
    # 1. Total vehicle kilometers travelled (all vehicles)
    total_vkt = sum(trip['routeLength'] for trip in trips) / 1000  # Convert m to km
    kpis['total_vkt_km'] = total_vkt
    
    # 2. Total travel time (all vehicles)
    total_travel_time = sum(trip['duration'] for trip in trips)
    kpis['total_travel_time_sec'] = total_travel_time
    kpis['total_travel_time_hours'] = total_travel_time / 3600
    
    # 3. Average trip duration per vehicle
    avg_trip_duration = total_travel_time / len(trips)
    kpis['avg_trip_duration_sec'] = avg_trip_duration
    kpis['avg_trip_duration_min'] = avg_trip_duration / 60
    
    # 4. Average trip duration per kilometer
    total_distance = sum(trip['routeLength'] for trip in trips)
    if total_distance > 0:
        avg_duration_per_km = total_travel_time / (total_distance / 1000)
        kpis['avg_trip_duration_per_km'] = avg_duration_per_km  # seconds per km
    else:
        kpis['avg_trip_duration_per_km'] = 0
    
    # 5. Average bus speed
    if bus_trips:
        total_bus_distance = sum(trip['routeLength'] for trip in bus_trips)
        total_bus_time = sum(trip['duration'] for trip in bus_trips)
        if total_bus_time > 0:
            avg_bus_speed = (total_bus_distance / 1000) / (total_bus_time / 3600)  # km/h
            kpis['avg_bus_speed_kmh'] = avg_bus_speed
        else:
            kpis['avg_bus_speed_kmh'] = 0
    else:
        kpis['avg_bus_speed_kmh'] = None  # No buses in dataset
    
    # 6. Average bus trip duration
    if bus_trips:
        avg_bus_duration = sum(trip['duration'] for trip in bus_trips) / len(bus_trips)
        kpis['avg_bus_trip_duration_sec'] = avg_bus_duration
        kpis['avg_bus_trip_duration_min'] = avg_bus_duration / 60
    else:
        kpis['avg_bus_trip_duration_sec'] = None
        kpis['avg_bus_trip_duration_min'] = None
    
    # 7. Total public transport (bus) distance travelled
    if bus_trips:
        total_bus_distance = sum(trip['routeLength'] for trip in bus_trips) / 1000  # km
        kpis['total_bus_distance_km'] = total_bus_distance
        kpis['num_buses'] = len(bus_trips)
    else:
        kpis['total_bus_distance_km'] = 0
        kpis['num_buses'] = 0
    
    # 8. Total delays (timeloss)
    total_delays = sum(trip['timeLoss'] for trip in trips)
    kpis['total_delays_sec'] = total_delays
    kpis['total_delays_hours'] = total_delays / 3600
    
    # Average delay per vehicle
    avg_delay = total_delays / len(trips)
    kpis['avg_delay_per_vehicle_sec'] = avg_delay
    kpis['avg_delay_per_vehicle_min'] = avg_delay / 60
    
    # 9. Congestion level (average waiting time)
    total_waiting_time = sum(trip['waitingTime'] for trip in trips)
    avg_waiting_time = total_waiting_time / len(trips)
    kpis['avg_waiting_time_sec'] = avg_waiting_time
    kpis['avg_waiting_time_min'] = avg_waiting_time / 60
    kpis['total_waiting_time_sec'] = total_waiting_time
    kpis['total_waiting_time_hours'] = total_waiting_time / 3600
    
    # Additional useful metrics
    kpis['num_vehicles'] = len(trips)
    kpis['avg_distance_per_vehicle_km'] = total_vkt / len(trips)
    
    return kpis


def print_kpis(kpis, trips, bus_trips):
    """Print KPIs in a formatted manner."""
    
    print("\n" + "="*70)
    print("SUMO SIMULATION KPIs SUMMARY")
    print("="*70 + "\n")
    
    print("--- VEHICLE TRAVEL STATISTICS ---")
    print(f"Total number of vehicles: {kpis['num_vehicles']}")
    print(f"Total vehicle kilometers travelled (VKT): {kpis['total_vkt_km']:.2f} km")
    print(f"Average distance per vehicle: {kpis['avg_distance_per_vehicle_km']:.2f} km")
    print(f"\nTotal travel time: {kpis['total_travel_time_hours']:.2f} hours ({kpis['total_travel_time_sec']:.0f} seconds)")
    
    print("\n--- TRIP DURATION METRICS ---")
    print(f"Average trip duration per vehicle: {kpis['avg_trip_duration_min']:.2f} minutes ({kpis['avg_trip_duration_sec']:.2f} seconds)")
    print(f"Average trip duration per km: {kpis['avg_trip_duration_per_km']:.2f} seconds/km")
    
    if kpis['num_buses'] > 0:
        print("\n--- PUBLIC TRANSPORT (BUSES) ---")
        print(f"Number of bus trips: {kpis['num_buses']}")
        print(f"Total bus distance travelled: {kpis['total_bus_distance_km']:.2f} km")
        print(f"Average bus speed: {kpis['avg_bus_speed_kmh']:.2f} km/h")
        print(f"Average bus trip duration: {kpis['avg_bus_trip_duration_min']:.2f} minutes ({kpis['avg_bus_trip_duration_sec']:.2f} seconds)")
    else:
        print("\n--- PUBLIC TRANSPORT (BUSES) ---")
        print("No buses detected in the tripinfo file.")
    
    print("\n--- DELAYS AND CONGESTION ---")
    print(f"Total delays (timeloss): {kpis['total_delays_hours']:.2f} hours ({kpis['total_delays_sec']:.0f} seconds)")
    print(f"Average delay per vehicle: {kpis['avg_delay_per_vehicle_min']:.2f} minutes ({kpis['avg_delay_per_vehicle_sec']:.2f} seconds)")
    print(f"\nTotal waiting time: {kpis['total_waiting_time_hours']:.2f} hours ({kpis['total_waiting_time_sec']:.0f} seconds)")
    print(f"Congestion level (average waiting time per vehicle): {kpis['avg_waiting_time_min']:.2f} minutes ({kpis['avg_waiting_time_sec']:.2f} seconds)")
    
    print("\n" + "="*70 + "\n")


def save_kpis_to_file(kpis, output_file):
    """Save KPIs to a text file."""
    
    with open(output_file, 'w') as f:
        f.write("="*70 + "\n")
        f.write("SUMO SIMULATION KPIs SUMMARY\n")
        f.write("="*70 + "\n\n")
        
        for key, value in kpis.items():
            if isinstance(value, float):
                f.write(f"{key}: {value:.4f}\n")
            else:
                f.write(f"{key}: {value}\n")
        
        f.write("\n" + "="*70 + "\n")
    
    print(f"KPIs saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Extract KPIs from SUMO tripinfo.xml file'
    )
    parser.add_argument(
        '--tripinfo_file',
        type=str,        
        default='LuSTScenario-master/scenario/dua.static.tripinfo.xml',
        help='Path to the tripinfo.xml file',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='simulation_kpis_summary.txt',
        help='Optional: output file to save KPIs (default: print to console only)',
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    if not Path(args.tripinfo_file).exists():
        print(f"Error: File '{args.tripinfo_file}' not found.")
        exit(1)
    
    # Parse tripinfo file
    print(f"Parsing tripinfo file: {args.tripinfo_file}")
    kpis, trips, bus_trips = parse_tripinfo(args.tripinfo_file)
    
    # Print KPIs
    print_kpis(kpis, trips, bus_trips)
    
    # Save to file if requested
    if args.output:
        save_kpis_to_file(kpis, args.output)
