import streamlit as st
import pandas as pd
import os
from glob import glob
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt

# Load trajectory data
def load_data(file_path):
    df = pd.read_csv(file_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    return df

# Save labeled data
def save_labeled_data(df, file_path):
    if os.path.exists(file_path):
        existing_df = pd.read_csv(file_path)
        existing_df.update(df)
        df = existing_df
    df.to_csv(file_path, index=False)

# Create folium map with bounds
def create_folium_map_with_bounds(df, bounds):
    # Initialize map centered around the median coordinates
    m = folium.Map(location=[41, -70], zoom_start=5, tiles='OpenStreetMap')

    folium.TileLayer('https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png', 
                        attr='OpenSeaMap', name='OpenSeaMap', opacity=0.8).add_to(m)

    folium.TileLayer('http://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}', 
                        attr='World_Ocean_Base', name='World_Ocean_Base', opacity=0.7).add_to(m)

    folium.TileLayer('https://gis.ices.dk/gis/rest/services/ICES_reference_layers/ICES_Areas/MapServer/tile/{z}/{y}/{x}',
                        attr='ICES_Areas', name='ICES_Areas', opacity=0.8).add_to(m)

    folium.TileLayer('https://www.fao.org/fishery/geoserver/ows?service=WMS&request=GetLegendGraphic&format=image%2Fpng&width=20&height=20&layer=area%3AFAO_AREASMapServer/tile/{z}/{y}/{x}',
                        attr='ICES_Areas', name='ICES_Areas', opacity=0.8).add_to(m)


    folium.WmsTileLayer(
        url="https://mesonet.agron.iastate.edu/cgi-bin/wms/nexrad/n0r.cgi",
        name="test",
        fmt="image/png",
        layers="nexrad-n0r-900913",
        attr=u"Weather data © 2012 IEM Nexrad",
        transparent=True,
        overlay=True,
        control=True,
    ).add_to(m)

    folium.WmsTileLayer(
        url="https://www.fao.org/fishery/geoserver/service",
        name="FAO_AREAS",
        fmt="image/png",
        layers="1",
        attr=u"FAO Areas and its breakdown",
        transparent=True,
        overlay=True,
        control=True,
    ).add_to(m)

    folium.raster_layers.WmsTileLayer(url ='https://www.fao.org/fishery/geoserver/ows?',
                    layers = '1',
                    transparent = False, 
                    control = True,
                    fmt="image/png",
                    name = 'FAO_AREAS',
                    attr = 'im seeing this',
                    overlay = True,
                    show = True,
                    CRS = 'EPSG:900913',
                    version = '1.3.0',
                    ).add_to(m)

    # folium.LayerControl().add_to(m)

    m
    
    # Add trajectory lines
    for i in range(len(df) - 1):
        start_index = i
        end_index = i + 1
        segment_df = df.iloc[start_index:end_index + 1]
        color = 'green' if pd.notnull(segment_df['label'].iloc[0]) and pd.notnull(segment_df['label'].iloc[1]) else 'blue'
        folium.PolyLine(segment_df[['latitude', 'longitude']].values, color=color, weight=2.5, opacity=1).add_to(m)
    
    # Add markers with custom icons and row indices
    for i, row in df.iterrows():
        sog = row['sog']
        color = 'black' if sog == 0 else ('red' if 0.1 <= sog <= 5 else 'blue')
        icon_html = f"""
            <div style="transform: rotate({row['heading']}deg);">
                <svg width="20" height="20" viewBox="0 0 100 100">
                    <polygon points="50,10 70,70 30,70" style="fill:{color};stroke:black;stroke-width:2" />
                </svg>
            </div>
            <div style="color: black; font-size: 12px; text-align: center;">
                {i}
            </div>
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            icon=folium.DivIcon(html=icon_html)
        ).add_to(m)

    # Fit the map to the bounds
    m.fit_bounds(bounds)

    return m

# Plot timeline
def plot_timeline(df):
    fig, ax = plt.subplots()
    colors = ['green' if pd.notnull(df['label'].iloc[i]) and pd.notnull(df['label'].iloc[i+1]) else 'blue' for i in range(len(df)-1)]
    ax.plot(df.index, df['sog'], marker='o', color='blue', markerfacecolor='red', markeredgewidth=0.5)
    
    for i in range(len(df)-1):
        ax.plot([df.index[i], df.index[i+1]], [df['sog'].iloc[i], df['sog'].iloc[i+1]], color=colors[i])
    
    ax.set_xlabel('Row Index')
    ax.set_ylabel('SOG')
    ax.set_title('Trajectory SOG Timeline')
    
    return fig

# Streamlit App
def main():
    st.title("Fishing Gear Type Classification")

    # Sidebar for file selection
    st.sidebar.title("Select Vessel Trajectory CSV File")
    data_files = glob("data/*.csv")
    selected_file = st.sidebar.selectbox("Choose a file", data_files)

    if selected_file:
        # Load data once
        df = load_data(selected_file)
        st.write(f"Displaying data for vessel: {df['cfr'].iloc[0]}")

        # Ensure 'label' column exists
        if 'label' not in df.columns:
            df['label'] = None

        # Display total count of rows and percentage of labeled rows
        total_rows = len(df)
        labeled_rows = df['label'].notnull().sum()
        labeled_percentage = (labeled_rows / total_rows) * 100 if total_rows > 0 else 0
        st.sidebar.subheader("Total Rows")
        st.sidebar.write(total_rows)
        st.sidebar.subheader("Labeled Percentage")
        st.sidebar.write(f"{labeled_percentage:.2f}%")

        # Select range of rows to label
        start_index = st.sidebar.number_input("Start Index", min_value=0, max_value=total_rows-1, value=0)
        end_index = st.sidebar.number_input("End Index", min_value=0, max_value=total_rows-1, value=min(total_rows-1, 999))
        
        # Filter the dataframe based on the selected range
        df_filtered = df.iloc[start_index:end_index+1].copy()
        
        # Calculate bounds
        bounds = [
            [df_filtered['latitude'].min(), df_filtered['longitude'].min()],
            [df_filtered['latitude'].max(), df_filtered['longitude'].max()]
        ]
        
        # Display table with selected rows
        table_container = st.empty()
        table_container.write("Trajectory Data:")
        table_container.dataframe(df_filtered, height=300, width=0)
        
        # Create and display the folium map with bounds
        map_container = st.empty()
        with map_container:
            folium_static(create_folium_map_with_bounds(df_filtered, bounds), width=700, height=700)

        # Plot and display the timeline
        plot_container = st.empty()
        plot_container.pyplot(plot_timeline(df_filtered))

        # User selects the label for the selected segment
        st.sidebar.title("Label Trajectory Segment")
        label_options = [
            "In port", 
            "In transit from port",
            "In transit to port", 
            "Searching", 
            "Unknown",
            "PS - Purse seines",
            "SX - Seine nets (nei)",
            "TBB - Beam trawls",
            "OTB - Single boat bottom otter trawls",
            "PTB - Bottom pair trawls",
            "TBN - Bottom trawls nephrops trawls",
            "TBS - Bottom trawls shrimp trawls",
            "TB - Bottom trawls (nei)",
            "OTM - Single boat midwater otter trawls",
            "PTM - Midwater pair trawls",
            "TM - Midwater otter trawls (nei)",
            "OT - Otter trawls (nei)",
            "TX - Trawls (nei)",
            "SSC - Scottish seines",
            "SDN - Danish seines",
            "SPR - Pair seines",
            "SV - Boat seines",
            "SX - Seines (nei)",
            "GN - Gillnets (nei)",
            "GNS - Set gillnets (anchored)",
            "GNM - Driftnets",
            "GND - Encircling gillnets",
            "GNC - Combined gillnets-trammel nets",
            "GTR - Trammel nets",
            "GTN - Fixed gillnets (on stakes)",
            "FX - Gillnets and entangling nets (nei)",
            "GL - Gillnets (nei)",
            "FWR - weir",
            "FYK - Fyke nets",
            "FPN - Pound nets",
            "FIX - Traps (nei)",
            "FIR - Large ring nets",
            "FIC - Cast nets",
            "FIF - Lift nets",
            "FDX - Drifting (nei)",
            "FSN - Stationary uncovered pound nets",
            "FS - Traps (nei)",
            "FW - Weir traps",
            "FY - Fyke nets (nei)",
            "FWR - weir",
            "HLN - Handlines and pole-lines (hand-operated)",
            "LHP - Handlines and pole-lines (mechanized)",
            "LLS - Set longlines",
            "LLD - Drifting longlines",
            "LL - Longlines (nei)",
            "LTL - Trolling lines",
            "LX - Hooks and lines (nei)",
            "HAR - Harpoons",
            "HMP - Pumps",
            "HMD - Mechanized dredges",
            "HMX - Harvesting machines (nei)",
            "MIS - Gear nei",
            "SV - Boat seines",
            "RG - RECREATIONAL FISHING GEAR",
            "NK - GEAR NOT KNOW",
            "NO - No gear",
            "PUK - Bottom trawls - electric beam trawls (Pulse Beam)",
            "PUL - Bottom trawls - electric sumwing trawls (Pulse Wing)",
            "SUX - Surrounding nets (nei)",
            "OTP - Multiple bottom otter trawls",
            "TSP - Semipelagic trawls",
            "DRM - Mechanized dredges",
            "DRX - Dredges (nei)",
            "SDN - Danish seines",
            "FCO - Cover pots/Lantern nets",
            "LVT - Vertical lines",
            "MHI - Hand implements (Wrenching gear, Clamps, Tongs, Rakes, Spears)",
            "MPM - Pumps",
            "MEL - Electric fishing",
            "MPN - Pushnets",
            "MSP - Scoopnets",
            "MDR - Drive-in nets",
            "MDV - Diving",
            "SSC - Scottish seines",
            "SPR - pair seines"]
        
        
        selected_label = st.sidebar.selectbox("Select Label", label_options)

        # Add a labeling button
        if st.sidebar.button("Label Segment"):
            st.sidebar.write(f"Labeling rows {start_index} to {end_index} as '{selected_label}'")
            
            # Update the dataframe with the new labels
            df.loc[start_index:end_index, 'label'] = selected_label
            
            # Save the updated dataframe
            save_path = selected_file  # Save to existing file
            save_labeled_data(df, save_path)
            st.sidebar.success(f"Labels added to {save_path}")

        # Always update df_filtered with the current range and labels
        df_filtered = df.iloc[start_index:end_index+1].copy()

        # Update displayed data
        table_container.write("Trajectory Data:")
        table_container.dataframe(df_filtered, height=300, width=0)

        # Update the map
        with map_container:
            folium_static(create_folium_map_with_bounds(df_filtered, bounds), width=700, height=700)

        # Update the timeline
        plot_container.pyplot(plot_timeline(df_filtered))

if __name__ == "__main__":
    main()
