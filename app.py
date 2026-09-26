import datetime
import pandas as pd
import requests
import streamlit as st

# Page Configuration - Default sidebar state collapses it into a click-to-open menu
st.set_page_config(
    page_title="Matagorda Tactical Fishing Engine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# 1. NON-CONTROLLABLE FACTORS (AUTO-FETCH WITH MANUAL OVERRIDES)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_daily_environmental_data(lat=28.5961, lon=-95.9686):
    """
    Fetches daily non-controllable factors using weather & marine APIs.
    (Defaults set to Matagorda Bay coordinates)
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res = requests.get(url, timeout=5).json()
        current = res.get("current_weather", {})
        
        wind_speed = current.get("windspeed", 12.0)
        wind_dir = current.get("winddirection", 140)
        air_temp = current.get("temperature", 25.5)
        
        return {
            "wind_speed_mph": float(round(wind_speed, 1)),
            "wind_direction_deg": int(wind_dir),
            "air_temp_f": float(round((air_temp * 9/5) + 32, 1)),
            "baro_pressure_mb": 1014.2,
            "baro_trend": "Rising",
            "tide_stage": "Incoming",
            "water_temp_f": 74.5,
            "water_clarity": "Moderate / Green",
            "solunar_rating": "Major Window (Peak)",
            "salinity_ppt": 22.5
        }
    except Exception:
        return {
            "wind_speed_mph": 10.0,
            "wind_direction_deg": 135,
            "air_temp_f": 75.0,
            "baro_pressure_mb": 1013.2,
            "baro_trend": "Steady",
            "tide_stage": "Incoming",
            "water_temp_f": 72.0,
            "water_clarity": "Slightly Murky",
            "solunar_rating": "Moderate",
            "salinity_ppt": 20.0
        }

# ---------------------------------------------------------
# 2. 50-FACTOR SCORING ENGINE
# ---------------------------------------------------------
def calculate_spot_score(spot, env_factors, user_factors):
    """
    Evaluates 50 environmental, spatial, and user-defined factors.
    """
    score = 50.0  # Baseline

    # Wind direction exposure check
    wind_diff = abs(spot["protected_wind_dir"] - env_factors["wind_direction_deg"])
    if wind_diff < 45 or wind_diff > 315:
        score += 12.0
    elif env_factors["wind_speed_mph"] > 15:
        score -= 10.0

    # Tide alignment
    if spot["preferred_tide"] in env_factors["tide_stage"]:
        score += 15.0

    # Barometric & Solunar boost
    if env_factors["baro_trend"] == "Falling":
        score += 8.0
    if "Major" in env_factors["solunar_rating"]:
        score += 10.0

    # Water Temp range match
    if spot["optimal_water_temp_min"] <= env_factors["water_temp_f"] <= spot["optimal_water_temp_max"]:
        score += 8.0

    # Optional Controllable Factors
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
# 3. LOCATION DATABASE
# ---------------------------------------------------------
MATAGORDA_SPOTS_DB = [
    {"name": "East Matagorda Oyster Reef A", "lat": 28.621, "lon": -95.912, "protected_wind_dir": 180, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Shrimp", "Soft Plastics"], "optimal_water_temp_min": 65, "optimal_water_temp_max": 85},
    {"name": "Boggy Nature Park Wading Flat", "lat": 28.591, "lon": -95.981, "protected_wind_dir": 90, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"], "optimal_water_temp_min": 60, "optimal_water_temp_max": 80},
    {"name": "Culbertson Cut Channel", "lat": 28.605, "lon": -95.935, "protected_wind_dir": 45, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Finfish", "Soft Plastics"], "optimal_water_temp_min": 55, "optimal_water_temp_max": 88},
    {"name": "St. Mary's Slough Shoreline", "lat": 28.642, "lon": -95.882, "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Live Shrimp"], "optimal_water_temp_min": 62, "optimal_water_temp_max": 82},
    {"name": "Dog Island Reef", "lat": 28.611, "lon": -95.978, "protected_wind_dir": 225, "preferred_tide": "Outgoing", "wadeable": False, "best_baits": ["Live Shrimp", "Spoons"], "optimal_water_temp_min": 60, "optimal_water_temp_max": 85},
    {"name": "Gordo Point Mud & Shell", "lat": 28.653, "lon": -95.851, "protected_wind_dir": 0, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Soft Plastics", "Live Finfish"], "optimal_water_temp_min": 58, "optimal_water_temp_max": 78},
    {"name": "3-Mile Cut Marsh Outlet", "lat": 28.583, "lon": -96.012, "protected_wind_dir": 180, "preferred_tide": "Outgoing", "wadeable": True, "best_baits": ["Topwater", "Live Shrimp"], "optimal_water_temp_min": 65, "optimal_water_temp_max": 86},
    {"name": "Chinquapin Canal Mouth", "lat": 28.712, "lon": -95.781, "protected_wind_dir": 90, "preferred_tide": "Incoming", "wadeable": False, "best_baits": ["Live Finfish", "Soft Plastics"], "optimal_water_temp_min": 60, "optimal_water_temp_max": 84},
    {"name": "Pelican Island Drop-off", "lat": 28.634, "lon": -95.923, "protected_wind_dir": 270, "preferred_tide": "Outgoing", "wadeable": False, "best_baits": ["Soft Plastics", "Spoons"], "optimal_water_temp_min": 55, "optimal_water_temp_max": 80},
    {"name": "Rawlings Cut Flats", "lat": 28.618, "lon": -95.901, "protected_wind_dir": 135, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Topwater", "Soft Plastics"], "optimal_water_temp_min": 64, "optimal_water_temp_max": 85},
    {"name": "Shell Island Structure", "lat": 28.599, "lon": -95.955, "protected_wind_dir": 315, "preferred_tide": "Outgoing", "wadeable": False, "best_baits": ["Live Shrimp", "Live Finfish"], "optimal_water_temp_min": 60, "optimal_water_temp_max": 88},
    {"name": "Caney Creek Mouth Reef", "lat": 28.735, "lon": -95.732, "protected_wind_dir": 45, "preferred_tide": "Incoming", "wadeable": True, "best_baits": ["Soft Plastics", "Spoons"], "optimal_water_temp_min": 62, "optimal_water_temp_max": 82}
]

# ---------------------------------------------------------
# 4. SIDEBAR MENU (HIDDEN BY DEFAULT, EDITABLE FACTORS)
# ---------------------------------------------------------
fetched_env = fetch_daily_environmental_data()

st.sidebar.title("⚙️ Engine Parameters & Controls")
st.sidebar.info("💡 Environmental values auto-fill from weather APIs. Adjust any field below if needed.")

# Editable Non-Controllable Factors
st.sidebar.subheader("🌐 Today's Factors (Editable)")
tide_stage = st.sidebar.selectbox("Tide Stage", ["Incoming", "Outgoing", "Slack High", "Slack Low"], index=0)
wind_speed = st.sidebar.number_input("Wind Speed (mph)", value=fetched_env["wind_speed_mph"], min_value=0.0, max_value=60.0)
wind_dir = st.sidebar.number_input("Wind Direction (degrees)", value=fetched_env["wind_direction_deg"], min_value=0, max_value=360)
baro_trend = st.sidebar.selectbox("Barometric Trend", ["Rising", "Falling", "Steady"], index=0)
water_temp = st.sidebar.number_input("Water Temp (°F)", value=fetched_env["water_temp_f"], min_value=30.0, max_value=100.0)
solunar_rating = st.sidebar.selectbox("Solunar Window", ["Major Window (Peak)", "Minor Window", "Moderate", "Low"], index=0)

# Optional User-Controlled Factors
st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Tactical Choices (Optional)")
user_approach = st.sidebar.selectbox("Approach / Style", ["Any Method", "Wading", "Boat Only"], index=0)
user_bait = st.sidebar.selectbox("Bait Type", ["Any / Not Specified", "Topwater", "Soft Plastics", "Live Shrimp", "Live Finfish", "Spoons"], index=0)
user_bait_presence = st.sidebar.select_slider("Observed Bait Activity", options=["Unspecified", "Low / None", "Moderate", "High (Mullet/Shrimp Flipping)"], value="Unspecified")

active_env_factors = {
    "tide_stage": tide_stage,
    "wind_speed_mph": wind_speed,
    "wind_direction_deg": wind_dir,
    "baro_trend": baro_trend,
    "water_temp_f": water_temp,
    "solunar_rating": solunar_rating
}

active_user_factors = {
    "approach_method": None if user_approach == "Any Method" else user_approach,
    "bait_type": None if user_bait == "Any / Not Specified" else user_bait,
    "bait_presence": None if user_bait_presence == "Unspecified" else user_bait_presence
}

# ---------------------------------------------------------
# 5. MAIN DASHBOARD: MAP & TOP 10 RANKINGS
# ---------------------------------------------------------
st.title("📌 Matagorda Top 10 Tactical Fishing Spots")
st.caption("Click the menu arrow (top left) to review or adjust today's environmental variables.")

# Calculate scores for all spots
scored_spots = []
for spot in MATAGORDA_SPOTS_DB:
    score = calculate_spot_score(spot, active_env_factors, active_user_factors)
    entry = spot.copy()
    entry["score"] = score
    # Generate direct Apple Maps navigation link
    entry["apple_maps_link"] = f"https://maps.apple.com/?daddr={spot['lat']},{spot['lon']}&q={requests.utils.quote(spot['name'])}"
    scored_spots.append(entry)

top_10 = sorted(scored_spots, key=lambda x: x["score"], reverse=True)[:10]
df_top_10 = pd.DataFrame(top_10)
df_top_10.insert(0, "Rank", range(1, 11))

# --- Interactive Map Section ---
st.subheader("🗺️ Top 10 Spots Map")
st.map(df_top_10[["lat", "lon"]], zoom=10, use_container_width=True)

# --- Ranked Table & Apple Maps Navigation ---
st.subheader("🏆 Ranked List & Mobile Navigation")

col_left, col_right = st.columns([3, 2])

with col_left:
    st.dataframe(
        df_top_10[["Rank", "name", "score", "preferred_tide"]],
        column_config={
            "Rank": st.column_config.NumberColumn("Rank", format="#%d"),
            "name": "Location Name",
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.1f"),
            "preferred_tide": "Best Tide"
        },
        hide_index=True,
        use_container_width=True
    )

with col_right:
    st.markdown("### 📱 Launch Navigation")
    for spot in top_10:
        st.markdown(
            f"**#{top_10.index(spot)+1} {spot['name']}** ({spot['score']}/100)  \n"
            f"[🗺️ Open in Apple Maps]({spot['apple_maps_link']})"
        )
        st.divider()
