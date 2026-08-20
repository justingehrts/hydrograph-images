import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import timedelta
import numpy as np

# --- 1. Define Gauge and Endpoints ---
GAGE_ID = "ISVO1"  # South Fork Licking River
meta_url = f"https://api.water.noaa.gov/nwps/v1/gauges/{GAGE_ID}"
data_url = f"https://api.water.noaa.gov/nwps/v1/gauges/{GAGE_ID}/stageflow"

# Set up local timezone for Ohio
local_tz = ZoneInfo("America/New_York")

# --- 2. Fetch Metadata (Flood Stages) ---
meta_resp = requests.get(meta_url).json()
gage_name = meta_resp.get("name", GAGE_ID)
flood_cats = meta_resp.get("flood", {}).get("categories", {})
stages = {
    "Action": flood_cats.get("action", {}).get("stage"),
    "Minor": flood_cats.get("minor", {}).get("stage"),
    "Moderate": flood_cats.get("moderate", {}).get("stage"),
    "Major": flood_cats.get("major", {}).get("stage")
}

# --- 3. Fetch Timeseries Data ---
data_resp = requests.get(data_url).json()

def parse_series(series_data, is_obs=False):
    times, heights = [], []
    current_time = datetime.now(local_tz)
    
    for pt in series_data:
        val = pt["primary"]
        
        # 1. Filter out NWPS missing data flags (e.g., -9999)
        if val is None or val < -100:
            continue
            
        dt_utc = datetime.fromisoformat(pt["validTime"].replace("Z", "+00:00"))
        local_dt = dt_utc.astimezone(local_tz)
        
        # 2. Trim observed data to only show the past 2 days
        if is_obs and (current_time - local_dt) > timedelta(days=2):
            continue
            
        times.append(local_dt)
        heights.append(val)
        
    return times, heights

# Update the function calls to pass the new is_obs flag
obs_times, obs_stages = parse_series(data_resp.get("observed", {}).get("data", []), is_obs=True)
fcst_times, fcst_stages = parse_series(data_resp.get("forecast", {}).get("data", []), is_obs=False)

all_stages = obs_stages + fcst_stages
if not all_stages:
    raise ValueError("No stage data returned.")

# --- 4. Plotting Setup & Dynamic Scaling ---
fig, ax = plt.subplots(figsize=(10, 6), dpi=300)
fig.patch.set_facecolor('#dedede') # Match standard NWS gray border
ax.set_facecolor('#ffffff')

# Plot lines
if obs_times:
    ax.plot(obs_times, obs_stages, color='#1e90ff', linewidth=5, label='Observed')
if fcst_times:
    ax.plot(fcst_times, fcst_stages, color='#800080', linewidth=5, label='Forecast')

# Dynamic Y-Axis: Pad 2 feet above/below the max/min data OR flood stages
valid_thresholds = [s for s in stages.values() if s is not None]
y_min = np.floor(min(all_stages + valid_thresholds) - 2.0)
y_max = np.ceil(max(all_stages + valid_thresholds) + 2.0)
ax.set_ylim(y_min, y_max)

# Add flood category shading
colors = {"Action": "#ffff99", "Minor": "#ffcc66", "Moderate": "#ff9999", "Major": "#cc99ff"}
sorted_stages = sorted([(k, v) for k, v in stages.items() if v is not None], key=lambda x: x[1])

for i, (name, stage_val) in enumerate(sorted_stages):
    upper_bound = sorted_stages[i+1][1] if i + 1 < len(sorted_stages) else y_max
    ax.axhspan(stage_val, upper_bound, color=colors[name], alpha=0.5)
    ax.axhline(stage_val, color='black', linewidth=1)
    ax.text(obs_times[0] if obs_times else fcst_times[0], stage_val + 0.1, f' {name}: {stage_val}\'', color='black', fontsize=9, weight='bold')

# --- 5. Aesthetics ---
#ax.set_title(f"{gage_name.upper()}", fontsize=14, weight='bold', color='#000080', pad=15)
ax.set_ylabel("Stage (ft)", fontsize=12, weight='bold')
#ax.set_xlabel("Site Time (EDT/EST)", fontsize=12, weight='bold')

# X-axis date formatting
ax.xaxis.set_major_formatter(mdates.DateFormatter('%a\n%b %d', tz=local_tz))
ax.grid(True, linestyle=':', color='gray')
#ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False)

plt.tight_layout()
plt.savefig("image_d0b471_dynamic.png", facecolor=fig.get_facecolor())
