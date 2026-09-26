import datetime
import json
import os
import pandas as pd
from PIL import Image
import requests
import folium
from streamlit_folium import st_folium
import streamlit as st
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

# Load or initialize saved lures for autofill
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
# 2. WAYPOINT DATABASE
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
}

# ==============================================================================
# 3. TELEMETRY & API FETCH
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


# Navigation Tabs
tab1, tab2, tab3 = st.tabs(
    ["🗺️ Real-Time GPS & Map", "📸 Log a Catch", "📊 Catch History & Analytics"]
)

# ==============================================================================
# TAB 1: REAL-TIME GPS & MAP
# ==============================================================================
with tab1:
    st.header("📍 Live GPS Location & Marine Telemetry")

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

    telemetry = fetch_telemetry(current_lat, current_lon)

    with col_gps2:
        col_w1, col_w2, col_w3, col_w4 = st.columns(4)
        col_w1.metric("Air Temp", f"{telemetry['air_temp']} °F")
        col_w2.metric("Water Temp", f"{telemetry['water_temp']} °F")
        col_w3.metric(
            "Wind", f"{telemetry['wind_speed']} kts {telemetry['wind_dir']}"
        )
        col_w4.metric("Tide Level", f"{telemetry['water_level']} ft")

    st.subheader("🗺️ Interactive Navigation Map")
    m = folium.Map(
        location=[current_lat, current_lon],
        zoom_start=12 if loc else 11,
        tiles="OpenStreetMap",
    )

    # Highlight Live User Position if available
    if loc and "coords" in loc:
        folium.Marker(
            location=[current_lat, current_lon],
            popup="<b>Your Current Location</b>",
            tooltip="You Are Here",
            icon=folium.Icon(color="red", icon="user"),
        ).add_to(m)

    # Waypoint Markers
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
# TAB 2: LOG A CATCH WITH AUTOFILL LURE MEMORY
# ==============================================================================
with tab2:
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

        # LURE AUTOFILL / AUTOCOMPLETE IMPLEMENTATION
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
                # Save new lure to memory file if it's not already in the list
                if final_lure not in saved_lures:
                    saved_lures.append(final_lure)
                    with open(LURES_FILE, "w") as f:
                        json.dump(saved_lures, f)

                # Save Image
                img_filename = f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_image.name}"
                img_path = os.path.join(IMAGE_DIR, img_filename)
                image.save(img_path)

                # Save Data
                new_data = {
                    "Timestamp": datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "Species": species,
                    "Length_Inches": length,
                    "Lure_Bait_Used": final_lure,
                    "Location_Name": location_caught,
                    "Fishing_Style": fishing_style,
                    "Air_Temp": telemetry["air_temp"],
                    "Water_Temp": telemetry["water_temp"],
                    "Wind": f"{telemetry['wind_speed']} kts {telemetry['wind_dir']}",
                    "Pressure": telemetry["pressure"],
                    "Water_Level": telemetry["water_level"],
                    "Photo_Path": img_path,
                }

                df_existing = pd.read_csv(LOG_FILE)
                df_updated = pd.concat(
                    [df_existing, pd.DataFrame([new_data])], ignore_index=True
                )
                df_updated.to_csv(LOG_FILE, index=False)

                st.success(
                    f"✅ Saved {length}\" {species} caught with {final_lure}! Lure saved to memory."
                )
            else:
                st.error(
                    "⚠️ Please upload a photo and specify the lure used before saving."
                )

# ==============================================================================
# TAB 3: CATCH HISTORY & ANALYTICS
# ==============================================================================
with tab3:
    st.header("📊 Personal Catch Database")
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