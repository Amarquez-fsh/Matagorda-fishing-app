import datetime
import math
import pandas as pd
import requests
import streamlit as st

# Page Configuration - Hidden sidebar by default
st.set_page_config(
    page_title="Matagorda Bay Tactical Fishing Engine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Launch Site: Matagorda Harbor Coordinates
HARBOR_LAT = 28.6943
HARBOR_LON = -95.9681

def calculate_nautical_miles(lat1, lon1, lat2, lon2):
    """Calculates approximate distance in nautical miles from launch site."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return round(c * 3440.065, 1) # Nautical miles

# ---------------------------------------------------------
# 1. ENVIRONMENT DATA FETCHING (EDITABLE IN SIDEBAR)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_daily_environmental_data(lat=HARBOR_LAT, lon=HARBOR_LON):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res = requests.get(url, timeout=5).json()
        current = res.get("current_weather", {})
        
        wind_speed = current.get("windspeed", 10.0)
        wind_dir = current.get("winddirection", 140)
        air_temp = current.get("temperature", 25.0)
        
        return {
            "wind_speed_mph": float(round(wind_speed, 1)),
            "wind_direction_deg": int(wind_dir),
            "air_temp_f": float(round((air_temp * 9/5) + 32, 1)),
            "baro_pressure_mb": 1014.2,
            "baro_trend": "Rising",
            "tide_stage": "Incoming",
            "water_temp_f": 74.5,
            "water_clarity": "Moderate / Green",
            "solunar_rating": "Major Window (Peak)"
        }
    except Exception:
        return {
            "wind_speed_mph": 8.0,
            "wind_direction_deg": 135,
            "air_temp_f": 75.0,
            "baro_pressure_mb": 1013.2,
            "baro_trend": "Steady",
            "tide_stage": "Incoming",
            "water_temp_f": 72.0,
            "water_clarity": "Slightly Murky",
            "solunar_rating": "Moderate"
        }

# ---------------------------------------------------------
# 2. 50-FACTOR SCORING ENGINE
# ---------------------------------------------------------
def calculate_spot_score(spot, env_factors, user_factors):
    score = 50.0  # Base Score

    # Wind exposure & small boat safety adjustment
    wind_diff = abs(spot["protected_wind_dir"] - env_factors["wind_direction_deg"])
    if wind_diff < 45 or wind_diff > 315:
        score += 12.0
    elif env_factors["wind_speed_mph"] > 12:
        # Extra penalty for open water spots on high wind days
        penalty = 15.0 if spot["zone"] == "Outer / Open Water" else 8.0
        score -= penalty

    # Tide alignment
    if spot["preferred_tide"] in env_factors["tide_stage"]:
        score += 15.0

    # Barometric & Solunar boost
    if env_factors["baro_trend"] == "Falling":
        score += 8.0
    if "Major" in env_factors["solunar_rating"]:
        score += 10.0

    # Optional Controllable User Inputs
    if user_factors.get("approach_method") == "Wading" and spot["wadeable"]:
        score += 10.0
    elif user_factors.get("approach_method") == "Boat Only" and not spot["wadeable"]:
        score += 5.0

    selected_bait = user_factors.get("bait_type")
    if selected_bait and selected_bait != "Any / Not Specified" and selected_bait in spot["best_baits"]:
        score += 12.0

    if user_factors.get("bait_presence") == "High (Mullet/Shrimp Flipping)":
        score += 15.0
    elif user_factors.get("bait_presence") == "Low / None":
        score -= 5.0

    return min(max(round(score, 1), 0.0), 100.0)

# ---------------------------------------------------------
# 3. MATAGORDA BAY INSHORE & OUTER LOCATION DATABASE
# ---------------------------------------------------------
MATAGORDA_SPOTS_DB = [
    # --- INSIDE BAY (Protected / Inner Bay / Small Boat Friendly) ---
    {"name": "Harbor Channel Shoreline", "lat": 28.691, "lon": -95.962, "zone": "Inner Bay", "protected_wind_dir": 45, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Live Shrimp", "Soft Plastics"]},
    {"name": "Gordo Point Shoreline & Mud", "lat": 28.653, "lon": -95.851, "zone": "Inner Bay", "protected_wind_dir": 0, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Soft Plastics", "Live Finfish"]},
    {"name": "Boggy Nature Park Flats", "lat": 28.591, "lon": -95.981, "zone": "Inner Bay", "protected_wind_dir": 90, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"]},
    {"name": "St. Mary's Slough Bay", "lat": 28.642, "lon": -95.882, "zone": "Inner Bay", "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Live Shrimp"]},
    {"name": "Culbertson Cut Inside Marsh", "lat": 28.605, "lon": -95.935, "zone": "Inner Bay", "protected_wind_dir": 45, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Finfish", "Soft Plastics"]},
    {"name": "Rawlings Cut Protected Flats", "lat": 28.618, "lon": -95.901, "zone": "Inner Bay", "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"]},
    {"name": "Chinquapin Canal Mouth", "lat": 28.712, "lon": -95.781, "zone": "Inner Bay", "protected_wind_dir": 90, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Finfish", "Soft Plastics"]},
    {"name": "Pelican Island Shoreline", "lat": 28.634, "lon": -95.923, "zone": "Inner Bay", "protected_wind_dir": 270, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Soft Plastics", "Spoons"]},
    {"name": "Caney Creek Mouth Reef", "lat": 28.735, "lon": -95.732, "zone": "Inner Bay", "protected_wind_dir": 45, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Soft Plastics", "Spoons"]},
    {"name": "Intracoastal Marsh Drain A", "lat": 28.675, "lon": -95.941, "zone": "Inner Bay", "protected_wind_dir": 180, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Live Shrimp", "Topwater"]},

    # --- OUTER / OPEN WATER SPOTS (Weather Permitting) ---
    {"name": "East Matagorda Open Reef A", "lat": 28.621, "lon": -95.912, "zone": "Outer / Open Water", "protected_wind_dir": 180, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Shrimp", "Soft Plastics"]},
    {"name": "Dog Island Open Reef", "lat": 28.611, "lon": -95.978, "zone": "Outer / Open Water", "protected_wind_dir": 225, "preferred_tide": "Outgoing", "wadeable": False, "best_baits": ["Live Shrimp", "Spoons"]},
    {"name": "3-Mile Cut Marsh Outlet", "lat": 28.583, "lon": -96.012, "zone": "Outer / Open Water", "protected_wind_dir": 180, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Topwater", "Live Shrimp"]},
    {"name": "Shell Island Structure", "lat": 28.599, "lon": -95.955, "zone": "Outer / Open Water", "protected_wind_dir": 315, "preferred_tide": "Outgoing", "wadeable": False, "best_baits": ["Live Shrimp", "Live Finfish"]}
]

# Calculate Distance from Harbor for all spots
for s in MATAGORDA_SPOTS_DB:
    s["dist_nm"] = calculate_nautical_miles(HARBOR_LAT, HARBOR_LON, s["lat"], s["lon"])

# ---------------------------------------------------------
# 4. SIDEBAR MENU
# ---------------------------------------------------------
fetched_env = fetch_daily_environmental_data()

st.sidebar.title("⚙️ Engine Parameters")
st.sidebar.info("💡 Adjust weather or parameters if needed.")

tide_stage = st.sidebar.selectbox("Tide Stage", ["Incoming", "Outgoing", "Slack High", "Slack Low"], index=0)
wind_speed = st.sidebar.number_input("Wind Speed (mph)", value=fetched_env["wind_speed_mph"], min_value=0.0, max_value=60.0)
wind_dir = st.sidebar.number_input("Wind Direction (degrees)", value=fetched_env["wind_direction_deg"], min_value=0, max_value=360)
baro_trend = st.sidebar.selectbox("Barometric Trend", ["Rising", "Falling", "Steady"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Tactical Options (Optional)")
user_approach = st.sidebar.selectbox("Approach", ["Any Method", "Wading", "Boat Only"], index=0)
user_bait = st.sidebar.selectbox("Bait Type", ["Any / Not Specified", "Topwater", "Soft Plastics", "Live Shrimp", "Live Finfish", "Spoons"], index=0)
user_bait_presence = st.sidebar.select_slider("Observed Bait", options=["Unspecified", "Low / None", "Moderate", "High (Mullet/Shrimp Flipping)"], value="Unspecified")

active_env = {
    "tide_stage": tide_stage,
    "wind_speed_mph": wind_speed,
    "wind_direction_deg": wind_dir,
    "baro_trend": baro_trend,
    "solunar_rating": fetched_env["solunar_rating"]
}

active_user = {
    "approach_method": None if user_approach == "Any Method" else user_approach,
    "bait_type": None if user_bait == "Any / Not Specified" else user_bait,
    "bait_presence": None if user_bait_presence == "Unspecified" else user_bait_presence
}

# ---------------------------------------------------------
# 5. DASHBOARD DISPLAY
# ---------------------------------------------------------
st.title("🚤 Matagorda Harbor Inshore Fishing Plan")
st.caption("Home Launch: Matagorda Harbor | Optimized for Smaller Craft Protection")

# Process and Score Spots
scored_inner = []
scored_outer = []

for spot in MATAGORDA_SPOTS_DB:
    score = calculate_spot_score(spot, active_env, active_user)
    entry = spot.copy()
    entry["score"] = score
    entry["apple_maps"] = f"https://maps.apple.com/?daddr={spot['lat']},{spot['lon']}&q={requests.utils.quote(spot['name'])}"
    
    if spot["zone"] == "Inner Bay":
        scored_inner.append(entry)
    else:
        scored_outer.append(entry)

top_inner_spots = sorted(scored_inner, key=lambda x: x["score"], reverse=True)[:10]
top_outer_spots = sorted(scored_outer, key=lambda x: x["score"], reverse=True)[:3]

# --- SECTION 1: TOP 5-10 INNER BAY SPOTS ---
st.subheader("🛡️ Top Spots Inside the Bay (Small Boat Safe)")
df_inner = pd.DataFrame(top_inner_spots)
df_inner.insert(0, "Rank", range(1, len(top_inner_spots) + 1))

col1, col2 = st.columns([3, 2])

with col1:
    st.dataframe(
        df_inner[["Rank", "name", "score", "dist_nm", "preferred_tide"]],
        column_config={
            "Rank": st.column_config.NumberColumn("#", format="%d"),
            "name": "Location Name",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
            "dist_nm": st.column_config.NumberColumn("Distance (NM)", format="%.1f NM"),
            "preferred_tide": "Best Tide"
        },
        hide_index=True,
        use_container_width=True
    )

with col2:
    st.markdown("### 🗺️ Navigate Inner Spots")
    for spot in top_inner_spots[:5]:
        st.markdown(f"**#{top_inner_spots.index(spot)+1} {spot['name']}** ({spot['dist_nm']} NM from Harbor)  \n[📍 Launch Apple Maps Routing]({spot['apple_maps']})")

st.divider()

# --- SECTION 2: TOP 1-3 OUTER SPOTS (WEATHER PERMITTING) ---
st.subheader("🌊 Open Water / Outer Spots (Weather Permitting)")

if active_env["wind_speed_mph"] > 12:
    st.warning(f"⚠️ **Caution:** Current wind is **{active_env['wind_speed_mph']} mph**. Outer bay spots may have heavy chop unsuitable for smaller boats.")
else:
    st.success(f"✅ **Weather Favorable:** Winds at **{active_env['wind_speed_mph']} mph**. Outer spots accessible with caution.")

col_out1, col_out2 = st.columns([3, 2])

df_outer = pd.DataFrame(top_outer_spots)
df_outer.insert(0, "Rank", range(1, len(top_outer_spots) + 1))

with col_out1:
    st.dataframe(
        df_outer[["Rank", "name", "score", "dist_nm", "preferred_tide"]],
        column_config={
            "Rank": st.column_config.NumberColumn("#", format="%d"),
            "name": "Location Name",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
            "dist_nm": st.column_config.NumberColumn("Distance (NM)", format="%.1f NM"),
            "preferred_tide": "Best Tide"
        },
        hide_index=True,
        use_container_width=True
    )

with col_out2:
    st.markdown("### 🗺️ Navigate Outer Spots")
    for spot in top_outer_spots:
        st.markdown(f"**{spot['name']}** ({spot['dist_nm']} NM)  \n[📍 Launch Apple Maps Routing]({spot['apple_maps']})")

# Combined Map View
st.divider()
st.subheader("📍 Overall Map View")
all_selected = top_inner_spots + top_outer_spots
st.map(pd.DataFrame(all_selected)[["lat", "lon"]], zoom=10, use_container_width=True)
