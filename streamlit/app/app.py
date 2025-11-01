import requests
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page
st.set_page_config(page_title="Events Safety API Dashboard", layout="wide")

# URL de base de l'API
BASE_URL = "http://backend:8000"

res = requests.get(f"{BASE_URL}/")
if res.status_code != 200:
    st.error("❌ Impossible de se connecter à l'API. Vérifiez que le backend est en cours d'exécution.")
    st.stop()
    
infos = res.json()

# Définition des endpoints disponibles
ENDPOINTS = infos["endpoints"].copy()
# supprime docs endpoint if exists
if "docs" in ENDPOINTS:
    del ENDPOINTS["docs"]

# Fonctions helper pour récupérer les noms depuis l'API
@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def get_units_mapping():
    """Récupère toutes les unités et retourne un dict {unit_id: name}"""
    try:
        response = requests.get(f"{BASE_URL}/units/", params={"limit": 1000}, timeout=5)
        if response.status_code == 200:
            units = response.json()
            return {unit['unit_id']: unit.get('name', f"Unit {unit['unit_id']}") for unit in units}
    except:
        pass
    return {}

@st.cache_data(ttl=300)
def get_persons_mapping():
    """Récupère toutes les personnes et retourne un dict {person_id: name}"""
    try:
        response = requests.get(f"{BASE_URL}/persons/", params={"limit": 1000}, timeout=5)
        if response.status_code == 200:
            persons = response.json()
            return {
                person['person_id']: f"{person.get('name', '')} {person.get('family_name', '')}".strip() or f"Person {person['person_id']}"
                for person in persons
            }
    except:
        pass
    return {}

# Charger les mappings
units_map = get_units_mapping()
persons_map = get_persons_mapping()


# Initialize session state for pagination
if 'skip' not in st.session_state:
    st.session_state.skip = 0
if 'limit' not in st.session_state:
    st.session_state.limit = 100
if 'selected_endpoint' not in st.session_state:
    st.session_state.selected_endpoint = "events"
if 'all_items' not in st.session_state:
    st.session_state.all_items = []

# Titre principal
st.title("Events Safety API Dashboard")

# Navigation bar avec boutons horizontaux
st.markdown("### Navigation")
cols = st.columns(len(ENDPOINTS))

for idx, (name, endpoint) in enumerate(ENDPOINTS.items()):
    with cols[idx]:
        if st.button(name, use_container_width=True, type="primary" if st.session_state.selected_endpoint == name else "secondary"):
            st.session_state.selected_endpoint = name
            st.session_state.skip = 0  # Reset pagination when changing endpoint
            st.session_state.all_items = []  # Reset items when changing endpoint
            st.rerun()

st.markdown("---")

# Récupération des données de l'endpoint sélectionné
current_endpoint = ENDPOINTS[st.session_state.selected_endpoint]
url_api = f"{BASE_URL}{current_endpoint}"

try:
    # Paramètres de pagination
    params = {
        "skip": st.session_state.skip,
        "limit": st.session_state.limit
    }
    
    response = requests.get(url_api, params=params, timeout=5)
    
    if response.status_code == 200:
        items = response.json()
        
        # Ajouter les nouveaux items à la liste existante
        if items:
            st.session_state.all_items.extend(items)
        
        # Affichage du titre de la section
        st.subheader(f"{st.session_state.selected_endpoint} - Données")
        
        if st.session_state.all_items:
            # Conversion en DataFrame
            df = pd.DataFrame(st.session_state.all_items)
            
            # Ajouter les noms lisibles pour les IDs
            if 'organizational_unit_id' in df.columns:
                df['unit_name'] = df['organizational_unit_id'].map(
                    lambda x: units_map.get(x, f"Unit {x}") if pd.notna(x) else None
                )
            
            if 'declared_by_id' in df.columns:
                df['declared_by_name'] = df['declared_by_id'].map(
                    lambda x: persons_map.get(x, f"Person {x}") if pd.notna(x) else None
                )
            
            if 'owner_id' in df.columns:
                df['owner_name'] = df['owner_id'].map(
                    lambda x: persons_map.get(x, f"Person {x}") if pd.notna(x) else None
                )
            
            # Gérer la date "extracted_date" March 2, 2024 format
            if 'extracted_date' in df.columns:
                df['extracted_date'] = pd.to_datetime(df['extracted_date'], errors='coerce').dt.date
            if 'extracted_time' in df.columns:
                df['extracted_time'] = pd.to_datetime(df['extracted_time'], errors='coerce').dt.time
            
            # Affichage du nombre d'éléments (en plus petit)
            st.caption(f"Nombre d'éléments affichés: {len(st.session_state.all_items)}")
            
            # Affichage du tableau
            st.dataframe(df, use_container_width=True, height=400)
            
            # Bouton pour charger plus d'éléments
            if len(items) == st.session_state.limit:
                if st.button("Charger plus d'éléments", use_container_width=True):
                    st.session_state.skip += st.session_state.limit
                    st.rerun()
            
            # === GRAPHIQUES ===
            st.markdown("---")
            st.subheader("📊 Visualisations")
            
            # Graphiques spécifiques selon l'endpoint
            if st.session_state.selected_endpoint == "events":
                # Graphique 1: Nombre d'events par unit
                if 'organizational_unit_id' in df.columns:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Nombre d'événements par unité")
                        # Remplacer les IDs par les noms
                        df_with_names = df.copy()
                        df_with_names['unit_name'] = df_with_names['organizational_unit_id'].map(
                            lambda x: units_map.get(x, f"Unit {x}")
                        )
                        
                        unit_counts = df_with_names['unit_name'].value_counts().reset_index()
                        unit_counts.columns = ['Unité', 'Nombre']
                        
                        fig1 = px.pie(unit_counts, values='Nombre', names='Unité', 
                                     title='Distribution des événements par unité')
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### Top 10 des unités")
                        fig2 = px.bar(unit_counts.head(10), x='Unité', y='Nombre',
                                     title='Top 10 des unités avec le plus d\'événements')
                        fig2.update_xaxes(tickangle=-45)
                        st.plotly_chart(fig2, use_container_width=True)
                
                # Graphique 2: Events par type
                if 'type' in df.columns:
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        st.markdown("#### Types d'événements")
                        type_counts = df['type'].value_counts().reset_index()
                        type_counts.columns = ['Type', 'Nombre']
                        
                        fig3 = px.bar(type_counts, x='Type', y='Nombre',
                                     title='Répartition par type d\'événement')
                        st.plotly_chart(fig3, use_container_width=True)
                    
                    with col4:
                        st.markdown("#### Classification des événements")
                        if 'classification' in df.columns:
                            class_counts = df['classification'].value_counts().reset_index()
                            class_counts.columns = ['Classification', 'Nombre']
                            
                            fig4 = px.pie(class_counts, values='Nombre', names='Classification',
                                         title='Distribution par classification')
                            st.plotly_chart(fig4, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "persons":
                # Graphiques pour les personnes
                if 'role' in df.columns:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Répartition par rôle")
                        role_counts = df['role'].value_counts().reset_index()
                        role_counts.columns = ['Rôle', 'Nombre']
                        
                        fig1 = px.pie(role_counts, values='Nombre', names='Rôle',
                                     title='Distribution des personnes par rôle')
                        st.plotly_chart(fig1, use_container_width=True)
                    
                    with col2:
                        st.markdown("#### Nombre de personnes par rôle")
                        fig2 = px.bar(role_counts, x='Rôle', y='Nombre',
                                     title='Effectif par rôle')
                        st.plotly_chart(fig2, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "measures":
                # Graphiques pour les mesures correctives
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'organizational_unit_id' in df.columns:
                        st.markdown("#### Mesures par unité")
                        # Remplacer les IDs par les noms
                        df_with_names = df.copy()
                        df_with_names['unit_name'] = df_with_names['organizational_unit_id'].map(
                            lambda x: units_map.get(x, f"Unit {x}")
                        )
                        
                        unit_counts = df_with_names['unit_name'].value_counts().reset_index()
                        unit_counts.columns = ['Unité', 'Nombre']
                        
                        fig1 = px.bar(unit_counts.head(10), x='Unité', y='Nombre',
                                     title='Top 10 des unités avec le plus de mesures')
                        fig1.update_xaxes(tickangle=-45)
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    if 'cost' in df.columns:
                        st.markdown("#### Distribution des coûts")
                        df_cost = df[df['cost'].notna()]
                        if len(df_cost) > 0:
                            fig2 = px.histogram(df_cost, x='cost', nbins=20,
                                              title='Distribution des coûts des mesures')
                            st.plotly_chart(fig2, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "risks":
                # Graphiques pour les risques
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'gravity' in df.columns:
                        st.markdown("#### Gravité des risques")
                        gravity_counts = df['gravity'].value_counts().reset_index()
                        gravity_counts.columns = ['Gravité', 'Nombre']
                        
                        fig1 = px.pie(gravity_counts, values='Nombre', names='Gravité',
                                     title='Distribution par gravité')
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    if 'probability' in df.columns:
                        st.markdown("#### Probabilité des risques")
                        prob_counts = df['probability'].value_counts().reset_index()
                        prob_counts.columns = ['Probabilité', 'Nombre']
                        
                        fig2 = px.bar(prob_counts, x='Probabilité', y='Nombre',
                                     title='Répartition par probabilité')
                        st.plotly_chart(fig2, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "units":
                # Graphiques pour les unités
                if 'location' in df.columns:
                    st.markdown("#### Unités par localisation")
                    location_counts = df['location'].value_counts().reset_index()
                    location_counts.columns = ['Localisation', 'Nombre']
                    
                    fig1 = px.bar(location_counts, x='Localisation', y='Nombre',
                                 title='Nombre d\'unités par localisation')
                    st.plotly_chart(fig1, use_container_width=True)
            
        else:
            st.warning("Aucune donnée disponible pour cet endpoint.")
            
    else:
        st.error(f"Erreur {response.status_code}: Impossible de récupérer les données")
        
except requests.exceptions.ConnectionError:
    st.error("Impossible de se connecter à l'API. Vérifiez que le backend est en cours d'exécution.")
except requests.exceptions.Timeout:
    st.error("La requête a expiré. Le serveur met trop de temps à répondre.")
except Exception as e:
    st.error(f"Une erreur s'est produite: {str(e)}")
