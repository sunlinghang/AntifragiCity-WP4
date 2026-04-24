import pandas as pd
import xml.etree.ElementTree as ET
import matplotlib.pyplot as plt


def summary_to_df(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    data = []
    for step in root.findall('step'):
        data.append(step.attrib)

    df = pd.DataFrame(data)
    cols_to_fix = [
        'time', 'loaded', 'inserted', 'running', 'waiting', 'ended',
        'arrived', 'collisions', 'teleports', 'halting', 'stopped',
        'meanWaitingTime', 'meanTravelTime', 'meanSpeed',
        'meanSpeedRelative', 'duration'
    ]
    df[cols_to_fix] = df[cols_to_fix].apply(pd.to_numeric, errors='coerce')

    keep_cols = [
        'time', 'loaded', 'inserted', 'running', 'waiting', 'ended',
        'arrived', 'teleports', 'meanWaitingTime', 'meanTravelTime', 'meanSpeed',
    ]
    df = df[keep_cols]

    return df


path_baseline = "LuSTScenario-master/scenario/baseline/dua.static.summary.xml"
path_close_1pct = "LuSTScenario-master/scenario/closure_1pct_8h-9h_20260423143905/dua.static.summary.xml"
path_close_2pct = "LuSTScenario-master/scenario/closure_2pct_8h-9h_20260423135004/dua.static.summary.xml"

df_baseline = summary_to_df(path_baseline)
df_close_1pct = summary_to_df(path_close_1pct)
df_close_2pct = summary_to_df(path_close_2pct)

dfs = {
    'Baseline': df_baseline,
    'Closure 1%': df_close_1pct,
    'Closure 2%': df_close_2pct
}

tts_baseline = df_baseline['running'].sum()
tts_close_1pct = df_close_1pct['running'].sum()
tts_close_2pct = df_close_2pct['running'].sum()

inserted_baseline = df_baseline['inserted'].iloc[-1]
inserted_close_1pct = df_close_1pct['inserted'].iloc[-1]
inserted_close_2pct = df_close_2pct['inserted'].iloc[-1]


plt.figure(figsize=(5, 4))
bars = plt.bar([0.2, 1, 1.8], [tts_baseline, tts_close_1pct, tts_close_2pct], alpha=0.9, width=0.4)
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval, f"{yval:.2e}",
             va='bottom', ha='center', fontsize=10)
plt.xticks([0.2, 1, 1.8], ['Baseline', 'Closure 1%', 'Closure 2%'])
plt.ylabel('Total Travel Time [s]')
plt.ylim([-0.5, 2.5])
plt.ylim([0, 5e8])
plt.grid(c='gray', linewidth=0.2, axis='y')
plt.tight_layout()
plt.savefig('total_travel_time_comparison.pdf', format='pdf')
plt.show()
plt.close()


plt.figure(figsize=(5, 4))
for label, df in dfs.items():
    df['time_hours'] = df['time'] / 3600
    mask = (df['time_hours'] >= 7) & (df['time_hours'] <= 24) & (df['time'] % 60 == 0)
    df_filtered = df[mask].copy()
    df_filtered['meanSpeed'] = df_filtered['meanSpeed'].rolling(window=10, center=True).mean()
    plt.plot(df_filtered['time_hours'], df_filtered['meanSpeed'], label=label, alpha=0.9)

plt.axvspan(8, 9, color='darkred', alpha=0.2, label='Closure Period')
plt.axvline(x=16, color='darkred', linestyle='--')
plt.axvline(x=21, color='darkred', linestyle='--')
plt.xlabel('Time [hours]')
plt.ylabel('Mean Speed [m/s]')
plt.xticks(range(8, 25, 2))
plt.xlim([7, 24])
plt.ylim([0, 14])
plt.legend()
plt.grid(c='gray', linewidth=0.2)
plt.tight_layout()
plt.savefig('mean_speed_comparison_hours.pdf', format='pdf')
plt.show()


plt.figure(figsize=(5, 4))
for label, df in dfs.items():
    df['time_hours'] = df['time'] / 3600
    mask = (df['time_hours'] >= 7) & (df['time_hours'] <= 24) & (df['time'] % 60 == 0)
    df_filtered = df[mask].copy()
    df_filtered['running'] = df_filtered['running'].rolling(window=10, center=True).mean()
    plt.plot(df_filtered['time_hours'], df_filtered['running'], label=label, alpha=0.9)

plt.axvspan(8, 9, color='darkred', alpha=0.2, label='Closure Period')
plt.axvline(x=16, color='darkred', linestyle='--')
plt.axvline(x=21, color='darkred', linestyle='--')
plt.xlabel('Time [hours]')
plt.ylabel('Number of vehicles in simulation [veh]')
plt.xticks(range(8, 25, 2))
plt.xlim([7, 24])
plt.legend()
plt.grid(c='gray', linewidth=0.2)
plt.tight_layout()
plt.savefig('num_veh_hours.pdf', format='pdf')
plt.show()

