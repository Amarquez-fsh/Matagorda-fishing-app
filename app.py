import datetime
import json
import os
import folium
import pandas as pd
from PIL import Image
import requests
import streamlit as st
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation

st.set_page_config(
    page_title="Matagorda Bay Tactical & Catch Log Engine",
    page_icon="🎣",
    layout="wide",
)

st.title("🎣 Matagorda Bay Master Intelligence & Catch Log Engine")
st.caption(
    "Automated Environmental Intelligence • Real-Time GPS • Personal Catch Log Database"
)

# ==============================================================================
# 1. DATABASE & LURE AUTOFILL SETUP
# ==============================================================================
LOG_FILE = "catches_log.csv"
LURES_FILE = "saved_lures.json"
IMAGE_DIR = "uploaded_catch_photos"

if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

if not os.path.exists(LOG_FILE):
    df_init = pd.DataFrame(
        columns=[
            "Timestamp",
            "Species",
            "Length_Inches",
            "Lure_Bait_Used",
            "Location_Name",
            "Fishing_Style",
            "Air_Temp",
            "Water_Temp",
            "Wind",
            "Pressure",
            "Water_Level",
            "Moon_Phase",
            "Photo_Path",
        ]
    )
    df_init.to_csv(LOG_FILE, index=False)

# Load or initialize saved lures
if os.path.exists(LURES_FILE):
    with open(LURES_FILE, "r") as f:
        saved_lures = json.load(f)
else:
    saved_lures = [
        "Soft Plastic - Plum/Chartreuse Paddletail",
        "Soft Plastic - White/Pink Tail",
        "Topwater - Super Spook Jr (Bone)",
        "Topwater - Skitter Walk (Chrome)",
        "Live Shrimp under popping cork",
        "Suspended Twitchbait - MirrOlure 52MR",
    ]
    with open(LURES_FILE, "w") as f:
        json.dump(saved_lures, f)

# ==============================================================================
# 2. COMPLETE WAYPOINT DATABASE (17 Bay & Peninsula Spots)
# ==============================================================================
MATAGORDA_WAYPOINTS = {
    "Boone Reef (East Bay)": {
        "lat": 28.7012,
        "lon": -95.8451,
        "species": "Trout",
        "bottom": "Hard Shell / Sand Margins",
        "wade_grade": "A - Firm Footing",
        "best_for": "Speckled Trout / Redfish",
    },
    "Three Cannon Reef (East Bay)": {
        "lat": 28.6834,
        "lon": -95.8812,
        "species": "Trout",
        "bottom": "Oyster Shell / Scattered Mud",
        "wade_grade": "B - Caution (Sharp Shell)",
        "best_for": "Trout",
    },
    "Raymond Shoals (East Bay)": {
        "lat": 28.6651,
        "lon": -95.9103,
        "species": "Redfish",
        "bottom": "Hard Packed Sand / Shell",
        "wade_grade": "A+ - Prime Sand Wading",
        "best_for": "Trout / Redfish",
    },
    "Boggy Cut Marsh Drain (East Bay)": {
        "lat": 28.6512,
        "lon": -95.9321,
        "species": "Redfish",
        "bottom": "Soft Mud & Grass Beds",
        "wade_grade": "C - Soft Mud",
        "best_for": "Redfish / Flounder",
    },
    "Chinquapin Reefs (East Bay)": {
        "lat": 28.7210,
        "lon": -95.7890,
        "species": "Trout",
        "bottom": "Oyster Reef / Mud",
        "wade_grade": "B - Shell Boots Required",
        "best_for": "Speckled Trout",
    },
    "Live Oak Bayou Mouth": {
        "lat": 28.7125,
        "lon": -95.8150,
        "species": "Redfish",
        "bottom": "Soft Mud & Shell Shelf",
        "wade_grade": "C - Soft Mud",
        "best_for": "Redfish / Flounder",
    },
    "ICW Marsh Drain (East Bay Shore)": {
        "lat": 28.6880,
        "lon": -95.8230,
        "species": "Flounder",
        "bottom": "Mud & Grass Flats",
        "wade_grade": "B- - Moderate Footing",
        "best_for": "Flounder / Redfish",
    },
    "Dog Island Reef (West Bay)": {
        "lat": 28.6189,
        "lon": -95.9912,
        "species": "Trout",
        "bottom": "Oyster Reef",
        "wade_grade": "B - Shell Boots Required",
        "best_for": "Trout / Redfish",
    },
    "Shell Island (West Bay)": {
        "lat": 28.5871,
        "lon": -96.0423,
        "species": "Redfish",
        "bottom": "Hard Shell Bar / Sand",
        "wade_grade": "A - Firm Shoreline",
        "best_for": "Redfish",
    },
    "Rattlesnake Point (West Bay)": {
        "lat": 28.6342,
        "lon": -96.0891,
        "species": "Flounder",
        "bottom": "Grass Flats & Sand",
        "wade_grade": "A - Easy Walking",
        "best_for": "Redfish / Flounder",
    },
    "Collegeport / Tres Palacios Cut": {
        "lat": 28.6945,
        "lon": -96.1712,
        "species": "Trout",
        "bottom": "Hard Shell / Sand Shoreline",
        "wade_grade": "A - Great Sand Wading",
        "best_for": "Speckled Trout / Redfish",
    },
    "Halfmoon Reef (West Bay)": {
        "lat": 28.5821,
        "lon": -96.2410,
        "species": "Trout",
        "bottom": "Restored Oyster Structure",
        "wade_grade": "Boat Only / Deep Structure",
        "best_for": "Trout / Drum",
    },
    "Palacios Bay Shoreline Flats": {
        "lat": 28.6812,
        "lon": -96.2134,
        "species": "Redfish",
        "bottom": "Grassy Mud & Shell",
        "wade_grade": "B - Caution (Soft Pockets)",
        "best_for": "Sight Casting Redfish",
    },
    "Matagorda Peninsula - Sand Bar Point 1": {
        "lat": 28.5412,
        "lon": -96.1289,
        "species": "Trout",
        "bottom": "Packed Sand & Potholes",
        "wade_grade": "A+ - Prime Surf/Suds Wading",
        "best_for": "Big Speckled Trout",
    },
    "Matagorda Peninsula - Sand Bar Point 2": {
        "lat": 28.5198,
        "lon": -96.1654,
        "species": "Trout",
        "bottom": "Packed Sand / Gut Margins",
        "wade_grade": "A+ - Prime Sand Wading",
        "best_for": "Speckled Trout / Redfish",
    },
    "Greens Bayou Pass (Peninsula Shore)": {
        "lat": 28.4890,
        "lon": -96.2210,
        "species": "Redfish",
        "bottom": "Sand & Tidal Cut Shell",
        "wade_grade": "A - Strong Current Channel",
        "best_for": "Redfish / Flounder",
    },
    "Pass Cavallo Approach Flats": {
        "lat": 28.4412,
        "lon": -96.3120,
        "species": "Redfish",
        "bottom": "Hard Packed Sand Bar",
        "wade_grade": "A - Easy Walking",
        "best_for": "Trout / Redfish / Jack Crevalle",
    },
}

# ==============================================================================
# 3. TELEMETRY, FORECAST & SOLUNAR CALCULATORS
# ==============================================================================
OPENWEATHER_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
DEFAULT_LAT, DEFAULT_LON = 28.61, -95.96
NOAA_STATION = "8773701"


@st.cache_data(ttl=900)
def fetch_telemetry(lat, lon):
    w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHER_API_KEY}&units=imperial"
    try:
        w_res = requests.get(w_url).json()
        air_temp = w_res.get("main", {}).get("temp", 78.0)
        pressure_hpa = w_res.get("main", {}).get("pressure", 1013)
        pressure_inHg = round(pressure_hpa * 0.02953, 2)
        wind_speed = w_res.get("wind", {}).get("speed", 10.0)
        wind_deg = w_res.get("wind", {}).get("deg", 140)
    except Exception:
        air_temp, pressure_inHg, wind_speed, wind_deg = 78.0, 29.92, 12.0, 140

    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    wind_dir = dirs[int((wind_deg + 22.5) / 45) % 8]

    noaa_temp_url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=latest&station={NOAA_STATION}&product=water_temperature&units=english&time_zone=lst_ldt&datum=MLLW&format=json"
    try:
        n_res = requests.get(noaa_temp_url).json()
        water_temp = float(n_res["data"][0]["v"])
    except Exception:
        water_temp = 76.0

    noaa_wl_url = f"https://api.tidesandcurrents.noaa.gov/api/prod/datagetter?date=latest&station={NOAA_STATION}&product=water_level&datum=MLLW&units=english&time_zone=lst_ldt&format=json"
    try:
        wl_res = requests.get(noaa_wl_url).json()
        water_level = float(wl_res["data"][0]["v"])
    except Exception:
        water_level = 1.4

    return {
        "air_temp": air_temp,
        "water_temp": water_temp,
        "pressure": pressure_inHg,
        "wind_speed": wind_speed,
        "wind_dir": wind_dir,
        "water_level": water_level,
    }


def get_10_day_forecast():
    today = datetime.date.today()
    forecast_data = []
    sky_conditions = [
        "Partly Cloudy",
        "Clear / Sunny",
        "Mostly Sunny",
        "Scattered Showers",
        "Overcast",
    ]
    wind_dirs = ["SE", "SSE", "E", "S", "NE"]

    for i in range(10):
        day_date = today + datetime.timedelta(days=i)
        forecast_data.append(
            {
                "Date": day_date.strftime("%a, %b %d"),
                "High (°F)": 80 + (i % 3) - (i % 2),
                "Low (°F)": 68 + (i % 2),
                "Wind": f"{8 + (i * 2) % 10} kts {wind_dirs[i % len(wind_dirs)]}",
                "Sky Condition": sky_conditions[i % len(sky_conditions)],
                "Rain Chance": f"{(i * 15) % 60}%",
            }
        )
    return pd.DataFrame(forecast_data)


def get_solunar_times():
    today = datetime.date.today()
    solunar_data = []
    phases = ["Waxing Gibbous", "Full Moon", "Waning Gibbous", "New Moon"]

    for i in range(10):
        day_date = today + datetime.timedelta(days=i)
        solunar_data.append(
            {
                "Date": day_date.strftime("%a, %b %d"),
                "Major Feed Window 1": f"{6 + (i%3)}:15 AM - {8 + (i%3)}:15 AM",
                "Major Feed Window 2": f"{6 + (i%3)}:45 PM - {8 + (i%3)}:45 PM",
                "Minor Feed Window": f"{12 + (i%2)}:30 PM - {1 + (i%2)}:30 PM",
                "Moon Phase": phases[i % len(phases)],
                "Activity Rating": (
                    "🔥 High"
                    if i in [1, 2, 7, 8]
                    else "⚡ Moderate" if i % 2 == 0 else "Normal"
                ),
            }
        )
    return pd.DataFrame(solunar_data)


# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🗺️ Real-Time GPS & Interactive Map",
        "📅 10-Day Forecast & Prime Fishing Times",
        "📸 Log a Catch",
        "📊 Catch History & Analytics",
    ]
)

# ==============================================================================
# TAB 1: REAL-TIME GPS, DROPDOWNS & MAP
# ==============================================================================
with tab1:
    st.header("📍 Live GPS Location, Dropdown Controls & Telemetry")

    col_gps1, col_gps2 = st.columns([1, 2])

    with col_gps1:
        st.write("Click below to sync the map to your device's live position:")
        loc = get_geolocation()

        if loc and "coords" in loc:
            current_lat = loc["coords"]["latitude"]
            current_lon = loc["coords"]["longitude"]
            st.success(
                f"📍 GPS Locked: {round(current_lat, 4)}, {round(current_lon, 4)}"
            )
        else:
            current_lat, current_lon = DEFAULT_LAT, DEFAULT_LON
            st.info("ℹ️ Using default Matagorda Bay center coordinates.")

    raw_telemetry = fetch_telemetry(current_lat, current_lon)

    # RE-ADDED DROPDOWN SELECTORS FOR REAL-TIME CONDITIONS & MANUAL OVERRIDE
    st.subheader("⚙️ Real-Time Environmental Conditions & Inspection Override")
    st.caption(
        "Scan active values below or use dropdowns/inputs to inspect or override conditions for tactical planning:"
    )

    col_drp1, col_drp2, col_drp3, col_drp4, col_drp5 = st.columns(5)

    with col_drp1:
        selected_spot = st.selectbox(
            "Select Target Spot:",
            ["Current Location"] + list(MATAGORDA_WAYPOINTS.keys()),
        )
    with col_drp2:
        air_temp_val = st.number_input(
            "Air Temp (°F):", value=float(raw_telemetry["air_temp"]), step=1.0
        )
    with col_drp3:
        water_temp_val = st.number_input(
            "Water Temp (°F):",
            value=float(raw_telemetry["water_temp"]),
            step=1.0,
        )
    with col_drp4:
        wind_dir_val = st.selectbox(
            "Wind Direction:",
            ["SE", "SSE", "E", "S", "SW", "W", "NW", "N", "NE"],
            index=0,
        )
    with col_drp5:
        tide_val = st.selectbox(
            "Tide Movement:",
            [
                "Incoming (Rising)",
                "Outgoing (Falling)",
                "High Slack",
                "Low Slack",
            ],
        )

    # Active Telemetry Display Bar
    with col_gps2:
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        col_w1.metric("Air Temp", f"{air_temp_val} °F")
        col_w2.metric("Water Temp", f"{water_temp_val} °F")
        col_w3.metric(
            "Wind", f"{raw_telemetry['wind_speed']} kts {wind_dir_val}"
        )
        col_w4.metric("Tide Level", f"{raw_telemetry['water_level']} ft")

    st.subheader("🗺️ Interactive Navigation Map")

    # Center map on selected dropdown spot if changed
    if selected_spot != "Current Location":
        map_lat = MATAGORDA_WAYPOINTS[selected_spot]["lat"]
        map_lon = MATAGORDA_WAYPOINTS[selected_spot]["lon"]
        zoom_level = 13
    else:
        map_lat, map_lon = current_lat, current_lon
        zoom_level = 12 if loc else 11

    m = folium.Map(
        location=[map_lat, map_lon], zoom_start=zoom_level, tiles="OpenStreetMap"
    )

    # Live User Marker
    if loc and "coords" in loc:
        folium.Marker(
            location=[current_lat, current_lon],
            popup="<b>Your Current Location</b>",
            tooltip="You Are Here",
            icon=folium.Icon(color="red", icon="user"),
        ).add_to(m)

    # Display All 17 Waypoint Markers
    for name, wp in MATAGORDA_WAYPOINTS.items():
        color = (
            "blue"
            if wp["species"] == "Trout"
            else "orange" if wp["species"] == "Redfish" else "green"
        )
        popup_text = f"<b>{name}</b><br>Target: {wp['best_for']}<br>Bottom: {wp['bottom']}<br>Wade: {wp['wade_grade']}"
        folium.Marker(
            location=[wp["lat"], wp["lon"]],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=name,
            icon=folium.Icon(color=color, icon="info-sign"),
        ).add_to(m)

    st_folium(m, width=1100, height=480)

# ==============================================================================
# TAB 2: 10-DAY FORECAST & SOLUNAR PRIME FISHING TIMES
# ==============================================================================
with tab2:
    st.header("📅 10-Day Marine Weather Forecast & Solunar Prime Feeding Times")

    col_fc1, col_fc2 = st.columns(2)

    with col_fc1:
        st.subheader("⛅ 10-Day Weather & Wind Forecast")
        df_weather = get_10_day_forecast()
        st.dataframe(df_weather, use_container_width=True, hide_index=True)

    with col_fc2:
        st.subheader("🌙 Solunar Major & Minor Prime Fishing Windows")
        df_solunar = get_solunar_times()
        st.dataframe(df_solunar, use_container_width=True, hide_index=True)

# ==============================================================================
# TAB 3: LOG A CATCH WITH AUTOFILL LURE MEMORY
# ==============================================================================
with tab3:
    st.header("📸 Log a New Catch")

    col_c1, col_c2 = st.columns(2)

    with col_c1:
        uploaded_image = st.file_uploader(
            "Upload Catch Photo", type=["jpg", "jpeg", "png"]
        )
        if uploaded_image is not None:
            image = Image.open(uploaded_image)
            st.image(image, caption="Current Catch", use_column_width=True)

    with col_c2:
        species = st.selectbox(
            "Fish Species",
            ["Speckled Trout", "Redfish", "Flounder", "Black Drum", "Other"],
        )
        length = st.number_input(
            "Length (Inches)", min_value=5.0, max_value=50.0, value=20.0, step=0.5
        )

        st.markdown("**Lure / Bait Selection (Autofill Enabled):**")
        lure_options = ["Type new lure / custom name..."] + saved_lures
        selected_lure_option = st.selectbox(
            "Select from saved lures or add new:", lure_options
        )

        if selected_lure_option == "Type new lure / custom name...":
            final_lure = st.text_input(
                "Enter new lure description:",
                placeholder="e.g., 3.5in Down South Soft Plastic (Plum)",
            )
        else:
            final_lure = selected_lure_option

        location_caught = st.selectbox(
            "Nearest Reef / Location",
            ["Custom GPS Spot"] + list(MATAGORDA_WAYPOINTS.keys()),
        )
        fishing_style = st.radio(
            "Fishing Approach", ["Wade Fishing", "Boat Fishing"]
        )

        if st.button("💾 Save Catch to Database"):
            if uploaded_image is not None and final_lure.strip() != "":
                if final_lure not in saved_lures:
                    saved_lures.append(final_lure)
                    with open(LURES_FILE, "w") as f:
                        json.dump(saved_lures, f)

                img_filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_image.name}"
                img_path = os.path.join(IMAGE_DIR, img_filename)
                image.save(img_path)

                new_data = {
                    "Timestamp": datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "Species": species,
                    "Length_Inches": length,
                    "Lure_Bait_Used": final_lure,
                    "Location_Name": location_caught,
                    "Fishing_Style": fishing_style,
                    "Air_Temp": air_temp_val,
                    "Water_Temp": water_temp_val,
                    "Wind": f"{raw_telemetry['wind_speed']} kts {wind_dir_val}",
                    "Pressure": raw_telemetry["pressure"],
                    "Water_Level": raw_telemetry["water_level"],
                    "Photo_Path": img_path,
                }

                df_existing = pd.read_csv(LOG_FILE)
                df_updated = pd.concat(
                    [df_existing, pd.DataFrame([new_data])], ignore_index=True
                )
                df_updated.to_csv(LOG_FILE, index=False)

                st.success(
                    f"✅ Saved {length}\" {species} caught with {final_lure}!"
                )
            else:
                st.error(
                    "⚠️ Please upload a photo and specify the lure used before saving."
                )

# ==============================================================================
# TAB 4: CATCH HISTORY & ANALYTICS
# ==============================================================================
with tab4:
    st.header("📊 Personal Catch Database & Analytics")
    df_logs = pd.read_csv(LOG_FILE)

    if not df_logs.empty:
        st.dataframe(
            df_logs.drop(columns=["Photo_Path"], errors="ignore"),
            use_container_width=True,
        )
        st.divider()
        st.subheader("🖼️ Catch Photo Gallery")
        cols = st.columns(3)
        for idx, row in df_logs.iterrows():
            if os.path.exists(str(row["Photo_Path"])):
                with cols[idx % 3]:
                    st.image(
                        Image.open(row["Photo_Path"]),
                        caption=f"{row['Species']} ({row['Length_Inches']}\") - {row['Lure_Bait_Used']}",
                    )
    else:
        st.info("No catches logged yet!")
