import streamlit as st
import folium
import requests
import pandas as pd
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster, HeatMap

# Settings
SETTINGS = {
    "MAIN_COLOR": "#023F02",
    "BG_COLOR": "#FFFFFF",
    "MAP_TILES": "CartoDB Positron",
    "DASHBOARD_TITLE": "🌲 Portland Heritage Trees"
}

st.set_page_config(
    layout="wide"
)


# Load data
@st.cache_data(ttl= 60*60)
def get_clean_data():
    url = "https://www.portlandmaps.com/arcgis/rest/services/Public/Parks_Misc/MapServer/21/query"
    params = {'where': '1=1', 'outFields': '*', 'f': 'geojson'}
    try:
        response = requests.get(url, params=params).json()
        rows = []
        for f in response['features']:
            props = f['properties']
            props['lat'] = f['geometry']['coordinates'][1]
            props['lon'] = f['geometry']['coordinates'][0]
            rows.append(props)
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = get_clean_data()

if not df.empty:
    st.title(SETTINGS["DASHBOARD_TITLE"])
    
    # === SIDEBAR FILTERS ===
    st.sidebar.header("🔍 Filters")
    
    # Species filter
    all_species = sorted(df['COMMON'].dropna().unique())
    choice = st.sidebar.selectbox("Tree Species:", ["All"] + all_species)
    
    # Height filter
    min_height = int(df['HEIGHT'].min())
    max_height = int(df['HEIGHT'].max())
    height_range = st.sidebar.slider(
        "Height Range (feet):",
        min_height, max_height,
        (min_height, max_height)
    )
    
    # Diameter filter
    min_diameter = int(df['DIAMETER'].min())
    max_diameter = int(df['DIAMETER'].max())
    diameter_range = st.sidebar.slider(
        "Diameter Range (inches):",
        min_diameter, max_diameter,
        (min_diameter, max_diameter)
    )
    
    st.sidebar.markdown("---")
    
    # Map visualization options
    st.sidebar.header("🗺️ Map Style")
    map_type = st.sidebar.radio(
        "Visualization Type:",
        ["Markers", "Marker Cluster", "HeatMap"]
    )
    
    # === APPLY FILTERS ===
    df_filtered = df.copy()
    
    # Species filter
    if choice != "All":
        df_filtered = df_filtered[df_filtered['COMMON'] == choice]
    
    # Height filter
    df_filtered = df_filtered[
        (df_filtered['HEIGHT'] >= height_range[0]) & 
        (df_filtered['HEIGHT'] <= height_range[1])
    ]
    
    # Diameter filter
    df_filtered = df_filtered[
        (df_filtered['DIAMETER'] >= diameter_range[0]) & 
        (df_filtered['DIAMETER'] <= diameter_range[1])
    ]
    
    # === LAYOUT ===
    col_map, col_stats = st.columns([2, 1])
    
    with col_map:
        st.subheader(f"Map View - {len(df_filtered)} Trees")
        
        # Create map (fixed center and zoom)
        m = folium.Map(
            location=[45.523, -122.676],
            zoom_start=12,
            tiles=SETTINGS["MAP_TILES"]
        )
        
        # Add visualization based on type
        if map_type == "HeatMap":
            locations = df_filtered[['lat', 'lon']].values.tolist()
            HeatMap(locations, radius=15, blur=10).add_to(m)
            
        elif map_type == "Marker Cluster":
            cluster = MarkerCluster().add_to(m)
            for _, row in df_filtered.iterrows():
                tooltip_html = f"<b>{row['COMMON']}</b><br>Height: {row['HEIGHT']} ft<br>Diameter: {row['DIAMETER']} in"
                folium.CircleMarker(
                    [row['lat'], row['lon']],
                    radius=8,
                    color=SETTINGS["MAIN_COLOR"],
                    fill=True,
                    fillOpacity=0.8,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True)
                ).add_to(cluster)
                
        else:  # Markers
            for _, row in df_filtered.iterrows():
                tooltip_html = f"<b>{row['COMMON']}</b><br>Height: {row['HEIGHT']} ft<br>Diameter: {row['DIAMETER']} in"
                folium.CircleMarker(
                    [row['lat'], row['lon']],
                    radius=8,
                    color=SETTINGS["MAIN_COLOR"],
                    fill=True,
                    fillOpacity=0.8,
                    tooltip=folium.Tooltip(tooltip_html, sticky=True)
                ).add_to(m)
        
        # Display map (no map state tracking)
        st_folium(m, width=900, height=700, returned_objects=[])
    
    with col_stats:
        st.subheader("📊 Statistics")
        
        # Metrics
        m1, m2 = st.columns(2)
        m1.metric("Total Trees", len(df_filtered))
        m2.metric("Species Count", df_filtered['COMMON'].nunique())
        
        m3, m4 = st.columns(2)
        m3.metric("Avg Height", f"{df_filtered['HEIGHT'].mean():.1f} ft")
        m4.metric("Avg Diameter", f"{df_filtered['DIAMETER'].mean():.1f} in")        
       
        
        st.markdown("---")
        
        # Data export
        st.subheader("💾 Export Data")
        csv = df_filtered.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Filtered Data (CSV)",
            data=csv,
            file_name="portland_trees_filtered.csv",
            mime="text/csv",
            use_container_width=True
        )
        
   
else:
    st.error("❌ Could not load data from Portland API")
    st.info("Please check your internet connection and try again.")