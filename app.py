import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from shapely.geometry import Point
import osmnx as ox
import networkx as nx
from streamlit_folium import st_folium
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Titolo dell'applicazione
st.title('Analisi della Connettività dei Quartieri di Milano')

# Barra laterale per i parametri
st.sidebar.header('Parametri di Analisi')

# Selezione dei servizi primari
available_services = ['supermarket', 'gym', 'school', 'hospital', 'pharmacy']

selected_services = st.sidebar.multiselect(
    'Seleziona i servizi primari di interesse:',
    available_services,
    default=['supermarket', 'pharmacy']
)

# Impostazione della modalità di trasporto
transport_mode = st.sidebar.selectbox(
    'Modalità di trasporto:',
    ['A piedi', 'In auto']
)

if transport_mode == 'A piedi':
    network_type = 'walk'
    speed = 5  # km/h
else:
    network_type = 'drive'
    speed = 40  # km/h

# Tempo massimo di viaggio
max_time = st.sidebar.slider(
    'Tempo massimo di viaggio (minuti):',
    min_value=5, max_value=60, value=15, step=5
)

# Caricamento dei dati
st.write('Caricamento dei dati...')

# Carica i confini dei quartieri
quartieri = gpd.read_file('quartieri_milano.geojson')

# Imposta la colonna geometrica attiva
quartieri = quartieri.set_geometry('geometry')

# Trasforma il CRS
quartieri = quartieri.to_crs(epsg=4326)

# Scarica la rete stradale
place = 'Milano, Italia'
G = ox.graph_from_place(place, network_type=network_type)

# Definisci i tag per i servizi selezionati
tags = {'amenity': selected_services}

# Scarica i punti di interesse
poi = ox.geometries_from_place(place, tags)

# Calcolo della connettività
st.write('Calcolo della connettività...')

# Funzione per calcolare l'isocrona
def calculate_isochrone(G, center_point, max_dist):
    center_node = ox.nearest_nodes(G, center_point.x, center_point.y)
    subgraph = nx.ego_graph(G, center_node, radius=max_dist, distance='length')
    nodes, edges = ox.graph_to_gdfs(subgraph)
    return nodes.unary_union.convex_hull

# Velocità in m/s
speed_m_per_sec = speed * 1000 / 3600
# Distanza massima in metri
max_distance = speed_m_per_sec * max_time * 60

connectivity_scores = []

for idx, row in quartieri.iterrows():
    centroid = row.geometry.centroid
    try:
        isochrone = calculate_isochrone(G, centroid, max_distance)
        services_in_area = poi[poi.intersects(isochrone)]
        score = len(services_in_area)
    except Exception as e:
        score = 0
    connectivity_scores.append(score)

quartieri['connettività'] = connectivity_scores

# Generazione della mappa
st.write('Generazione della mappa...')

# Normalizziamo i punteggi per la visualizzazione
quartieri['punteggio_norm'] = quartieri['connettività'] / quartieri['connettività'].max()

# Creiamo la mappa
m = folium.Map(location=[45.4642, 9.19], zoom_start=12)

# Aggiungiamo i quartieri
folium.Choropleth(
    geo_data=quartieri,
    name='Connettività',
    data=quartieri,
    columns=['NIL', 'punteggio_norm'],
    key_on='feature.properties.NIL',
    fill_color='YlGn',
    fill_opacity=0.7,
    line_opacity=0.2,
    legend_name='Punteggio di Connettività'
).add_to(m)

# Aggiungiamo i servizi (opzionale)
if st.sidebar.checkbox('Mostra i servizi sulla mappa'):
    for idx, row in poi.iterrows():
        geom = row.geometry
        if geom.geom_type == 'Point':
            folium.CircleMarker(
                location=[geom.y, geom.x],
                radius=2,
                color='blue',
                fill=True,
                fill_color='blue'
            ).add_to(m)
        elif geom.geom_type == 'MultiPoint':
            for point in geom.geoms:
                folium.CircleMarker(
                    location=[point.y, point.x],
                    radius=2,
                    color='blue',
                    fill=True,
                    fill_color='blue'
                ).add_to(m)

# Visualizziamo la mappa
st_data = st_folium(m, width=700)

# Mostrare i risultati
st.header('Risultati')

# Ordiniamo i quartieri per punteggio
quartieri = quartieri.sort_values(by='connettività', ascending=False)

# Mostriamo i primi 10 quartieri
st.write(quartieri[['NIL', 'connettività']].head(10))
