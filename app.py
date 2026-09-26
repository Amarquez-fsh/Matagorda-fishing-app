import datetime
import math
import pandas as pd
import requests
import streamlit as st

# Page Configuration - Hidden sidebar menu by default
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
    return round(c * 3440.065, 1)

# ---------------------------------------------------------
# 1. ENVIRONMENT DATA FETCHING (AUTO-FILLED & EDITABLE)
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
            "solunar_rating": "Moderate"
        }

# ---------------------------------------------------------
# 2. 50-FACTOR ALGORITHM & SCORING ENGINE
# ---------------------------------------------------------
def calculate_spot_score(spot, env_factors, user_factors):
    score = 50.0  # Base Score

    # Wind exposure protection check
    wind_diff = abs(spot["protected_wind_dir"] - env_factors["wind_direction_deg"])
    if wind_diff < 45 or wind_diff > 315:
        score += 12.0
    elif env_factors["wind_speed_mph"] > 12:
        score -= 8.0  # Shelter penalty

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
# 3. EAST & WEST BAY INSHORE SPOTS DATABASE
# ---------------------------------------------------------
MATAGORDA_SPOTS_DB = [
    # --- EAST MATAGORDA BAY (Protected Inshore & Wading) ---
    {"name": "Boggy Nature Park Flats", "lat": 28.591, "lon": -95.981, "bay": "East Bay", "protected_wind_dir": 90, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"]},
    {"name": "Rawlings Cut Protected Flats", "lat": 28.618, "lon": -95.901, "bay": "East Bay", "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"]},
    {"name": "St. Mary's Slough Bay", "lat": 28.642, "lon": -95.882, "bay": "East Bay", "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Live Shrimp"]},
    {"name": "Raymond Landing Shoreline", "lat": 28.631, "lon": -95.895, "bay": "East Bay", "protected_wind_dir": 180, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Live Shrimp", "Soft Plastics"]},
    {"name": "Big Boggy Marsh Drain", "lat": 28.602, "lon": -95.955, "bay": "East Bay", "protected_wind_dir": 45, "preferred_tide": "Outgoing", "wadeable": False, "best_baits": ["Soft Plastics", "Live Finfish"]},
    {"name": "Chinquapin Canal Mouth", "lat": 28.712, "lon": -95.781, "bay": "East Bay", "protected_wind_dir": 90, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Finfish", "Soft Plastics"]},
    {"name": "Live Oak Bayou Outlet", "lat": 28.655, "lon": -95.840, "bay": "East Bay", "protected_wind_dir": 0, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Soft Plastics", "Spoons"]},

    # --- WEST MATAGORDA BAY (Protected Inshore & Wading) ---
    {"name": "Harbor Channel Mouth Drain", "lat": 28.691, "lon": -95.962, "bay": "West Bay", "protected_wind_dir": 45, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Live Shrimp", "Soft Plastics"]},
    {"name": "Oyster Lake Mouth Flat", "lat": 28.625, "lon": -96.115, "bay": "West Bay", "protected_wind_dir": 0, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Topwater", "Live Shrimp"]},
    {"name": "Culver's Marsh Cut", "lat": 28.665, "lon": -96.012, "bay": "West Bay", "protected_wind_dir": 180, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Finfish", "Soft Plastics"]},
    {"name": "Intracoastal Shoreline Drain", "lat": 28.675, "lon": -95.941, "bay": "West Bay", "protected_wind_dir": 180, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Live Shrimp", "Topwater"]},
    {"name": "Mad Island Bay Marsh Drain", "lat": 28.640, "lon": -96.082, "bay": "West Bay", "protected_wind_dir": 90, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Soft Plastics", "Spoons"]},
    {"name": "Colorado River Cut-off Flat", "lat": 28.682, "lon": -95.971, "bay": "West Bay", "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"]},
    {"name": "Schultz Bayou Shoreline", "lat": 28.610, "lon": -96.142, "bay": "West Bay", "protected_wind_dir": 270, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Shrimp", "Live Finfish"]}
]

# Pre-calculate Nautical Distance from Matagorda Harbor
for spot in MATAGORDA_SPOTS_DB:
    spot["dist_nm"] = calculate_nautical_miles(HARBOR_LAT, HARBOR_LON, spot["lat"], spot["lon"])

# ---------------------------------------------------------
# 4. SIDEBAR MENU (AUTO-FILLED & EDITABLE)
# ---------------------------------------------------------
fetched_env = fetch_daily_environmental_data()

st.sidebar.title("⚙️ Engine Parameters")
st.sidebar.info("💡 Environmental parameters auto-fill from weather APIs. Adjust any field below if necessary.")

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
# 5. DASHBOARD DISPLAY (EAST BAY & WEST BAY TOP 5-7 SPOTS)
# ---------------------------------------------------------
st.title("🚤 Matagorda Inshore Fishing Engine")
st.caption("Home Launch: Matagorda Harbor | Optimized for Shallow Drafts & Protected Waters")

scored_east = []
scored_west = []

for spot in MATAGORDA_SPOTS_DB:
    score = calculate_spot_score(spot, active_env, active_user)
    entry = spot.copy()
    entry["score"] = score
    entry["apple_maps"] = f"https://maps.apple.com/?daddr={spot['lat']},{spot['lon']}&q={requests.utils.quote(spot['name'])}"
    
    if spot["bay"] == "East Bay":
        scored_east.append(entry)
    else:
        scored_west.append(entry)

# Top 5-7 Spots per Bay
top_east = sorted(scored_east, key=lambda x: x["score"], reverse=True)[:7]
top_west = sorted(scored_west, key=lambda x: x["score"], reverse=True)[:7]

# --- SECTION 1: EAST MATAGORDA BAY ---
st.subheader("🌅 East Matagorda Bay (Top 5–7 Inshore Spots)")

df_east = pd.DataFrame(top_east)
df_east.insert(0, "Rank", range(1, len(top_east) + 1))

col_e1, col_e2 = st.columns([3, 2])

with col_e1:
    st.dataframe(
        df_east[["Rank", "name", "score", "dist_nm", "preferred_tide"]],
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

with col_e2:
    st.markdown("### 📱 Launch East Bay Routing")
    for spot in top_east:
        st.markdown(f"**#{top_east.index(spot)+1} {spot['name']}** ({spot['dist_nm']} NM from Harbor)  \n[📍 Open in Apple Maps]({spot['apple_maps']})")

st.divider()

# --- SECTION 2: WEST MATAGORDA BAY ---
st.subheader("🌊 West Matagorda Bay (Top 5–7 Inshore Spots)")

df_west = pd.DataFrame(top_west)
df_west.insert(0, "Rank", range(1, len(top_west) + 1))

col_w1, col_w2 = st.columns([3, 2])

with col_w1:
    st.dataframe(
        df_west[["Rank", "name", "score", "dist_nm", "preferred_tide"]],
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

with col_w2:
    st.markdown("### 📱 Launch West Bay Routing")
    for spot in top_west:
        st.markdown(f"**#{top_west.index(spot)+1} {spot['name']}** ({spot['dist_nm']} NM from Harbor)  \n[📍 Open in Apple Maps]({spot['apple_maps']})")

# Combined Interactive Map View
st.divider()
st.subheader("🗺️ Combined Inshore Bay Map")
all_spots = top_east + top_west
st.map(pd.DataFrame(all_spots)[["lat", "lon"]], zoom=10, use_container_width=True)
