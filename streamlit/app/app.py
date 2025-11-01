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

# Fonction pour charger TOUTES les données d'un endpoint
@st.cache_data(ttl=60)  # Cache pendant 1 minute
def get_all_data(endpoint_url):
    """Récupère toutes les données d'un endpoint en gérant la pagination"""
    all_items = []
    skip = 0
    limit = 1000
    
    while True:
        try:
            response = requests.get(endpoint_url, params={"skip": skip, "limit": limit}, timeout=10)
            if response.status_code == 200:
                items = response.json()
                if not items:
                    break
                all_items.extend(items)
                if len(items) < limit:
                    break
                skip += limit
            else:
                break
        except:
            break
    
    return all_items

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
            
            # === FILTRES ET TRI ===
            with st.expander("🔍 Filtres et options d'affichage", expanded=False):
                filter_col1, filter_col2 = st.columns(2)
                
                with filter_col1:
                    st.markdown("**Filtrer les données**")
                    
                    # Sélection de la colonne à filtrer
                    filter_column = st.selectbox(
                        "Colonne à filtrer",
                        ["Aucun"] + list(df.columns),
                        key="filter_column"
                    )
                    
                    if filter_column != "Aucun":
                        # Type de filtre selon le type de colonne
                        if df[filter_column].dtype in ['int64', 'float64']:
                            # Filtre numérique avec opérateur
                            filter_operator = st.selectbox(
                                "Opérateur",
                                ["=", "≠", ">", "<", "≥", "≤", "Entre"],
                                key="filter_operator"
                            )
                            
                            if filter_operator == "Entre":
                                col_min, col_max = st.columns(2)
                                with col_min:
                                    min_val = st.number_input("Min", value=float(df[filter_column].min()), key="min_val")
                                with col_max:
                                    max_val = st.number_input("Max", value=float(df[filter_column].max()), key="max_val")
                                df = df[(df[filter_column] >= min_val) & (df[filter_column] <= max_val)]
                            else:
                                filter_value = st.number_input(
                                    f"Valeur",
                                    value=float(df[filter_column].median()),
                                    key="filter_value"
                                )
                                if filter_operator == "=":
                                    df = df[df[filter_column] == filter_value]
                                elif filter_operator == "≠":
                                    df = df[df[filter_column] != filter_value]
                                elif filter_operator == ">":
                                    df = df[df[filter_column] > filter_value]
                                elif filter_operator == "<":
                                    df = df[df[filter_column] < filter_value]
                                elif filter_operator == "≥":
                                    df = df[df[filter_column] >= filter_value]
                                elif filter_operator == "≤":
                                    df = df[df[filter_column] <= filter_value]
                        
                        elif pd.api.types.is_datetime64_any_dtype(df[filter_column]) or filter_column.endswith('_date') or 'date' in filter_column.lower():
                            # Filtre de date avec opérateur
                            filter_operator = st.selectbox(
                                "Opérateur",
                                ["Après", "Avant", "Entre", "Année =", "Année >", "Année <"],
                                key="filter_date_operator"
                            )
                            
                            if filter_operator == "Entre":
                                col_start, col_end = st.columns(2)
                                with col_start:
                                    start_date = st.date_input("Date de début", key="start_date")
                                with col_end:
                                    end_date = st.date_input("Date de fin", key="end_date")
                                
                                # Convertir la colonne en datetime si nécessaire
                                df_temp = df.copy()
                                df_temp[filter_column] = pd.to_datetime(df_temp[filter_column], errors='coerce')
                                df = df_temp[(df_temp[filter_column] >= pd.Timestamp(start_date)) & 
                                            (df_temp[filter_column] <= pd.Timestamp(end_date))]
                            
                            elif filter_operator in ["Année =", "Année >", "Année <"]:
                                year_value = st.number_input("Année", min_value=1900, max_value=2100, value=2023, step=1, key="year_value")
                                df_temp = df.copy()
                                df_temp[filter_column] = pd.to_datetime(df_temp[filter_column], errors='coerce')
                                df_temp['_year'] = df_temp[filter_column].dt.year
                                
                                if filter_operator == "Année =":
                                    df = df_temp[df_temp['_year'] == year_value].drop('_year', axis=1)
                                elif filter_operator == "Année >":
                                    df = df_temp[df_temp['_year'] > year_value].drop('_year', axis=1)
                                elif filter_operator == "Année <":
                                    df = df_temp[df_temp['_year'] < year_value].drop('_year', axis=1)
                            
                            else:
                                filter_date = st.date_input(
                                    "Date",
                                    key="filter_date"
                                )
                                df_temp = df.copy()
                                df_temp[filter_column] = pd.to_datetime(df_temp[filter_column], errors='coerce')
                                
                                if filter_operator == "Après":
                                    df = df_temp[df_temp[filter_column] > pd.Timestamp(filter_date)]
                                elif filter_operator == "Avant":
                                    df = df_temp[df_temp[filter_column] < pd.Timestamp(filter_date)]
                        
                        else:
                            # Filtre catégoriel (texte)
                            filter_type = st.radio(
                                "Type de filtre",
                                ["Sélection multiple", "Contient", "Ne contient pas"],
                                horizontal=True,
                                key="filter_text_type"
                            )
                            
                            if filter_type == "Sélection multiple":
                                unique_values = df[filter_column].dropna().unique().tolist()
                                if len(unique_values) > 0:
                                    selected_values = st.multiselect(
                                        f"Valeurs pour {filter_column}",
                                        unique_values,
                                        default=unique_values,
                                        key="filter_values"
                                    )
                                    if selected_values:
                                        df = df[df[filter_column].isin(selected_values)]
                            elif filter_type == "Contient":
                                search_text = st.text_input("Texte à rechercher", key="search_text")
                                if search_text:
                                    df = df[df[filter_column].astype(str).str.contains(search_text, case=False, na=False)]
                            elif filter_type == "Ne contient pas":
                                exclude_text = st.text_input("Texte à exclure", key="exclude_text")
                                if exclude_text:
                                    df = df[~df[filter_column].astype(str).str.contains(exclude_text, case=False, na=False)]
                
                with filter_col2:
                    # Sélection des colonnes à afficher
                    st.markdown("**Colonnes à afficher**")
                    selected_columns = st.multiselect(
                        "Sélectionnez les colonnes",
                        list(df.columns),
                        default=list(df.columns),
                        key="selected_columns"
                    )
                    
                    if selected_columns:
                        df = df[selected_columns]
                    
                    # Statistiques sur les données filtrées
                    st.markdown("**Statistiques**")
                    st.info(f"📊 {len(df)} lignes après filtrage")
                
                # Sélection des colonnes à afficher
            
            # Affichage du tableau filtré et trié
            st.dataframe(df, use_container_width=True, height=400)
            
            # Bouton pour télécharger les données filtrées
            col_download1, col_download2 = st.columns([3, 1])
            with col_download2:
                st.download_button(
                    label="📥 Télécharger les données affichées (CSV)",
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name=f"{st.session_state.selected_endpoint}_filtered.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Bouton pour charger plus d'éléments
            if len(items) == st.session_state.limit:
                if st.button("Charger plus d'éléments", use_container_width=True):
                    st.session_state.skip += st.session_state.limit
                    st.rerun()
            
            # === GRAPHIQUES ===
            st.markdown("---")
            st.subheader("📊 Visualisations")
            
            # Charger TOUTES les données pour les graphiques
            with st.spinner("Chargement de toutes les données pour les visualisations..."):
                all_data = get_all_data(url_api)
                df_all = pd.DataFrame(all_data) if all_data else df.copy()
                
                # Ajouter les noms lisibles pour les IDs dans df_all
                if 'organizational_unit_id' in df_all.columns:
                    df_all['unit_name'] = df_all['organizational_unit_id'].map(
                        lambda x: units_map.get(x, f"Unit {x}") if pd.notna(x) else None
                    )
                
                if 'declared_by_id' in df_all.columns:
                    df_all['declared_by_name'] = df_all['declared_by_id'].map(
                        lambda x: persons_map.get(x, f"Person {x}") if pd.notna(x) else None
                    )
                
                if 'owner_id' in df_all.columns:
                    df_all['owner_name'] = df_all['owner_id'].map(
                        lambda x: persons_map.get(x, f"Person {x}") if pd.notna(x) else None
                    )
            
            st.info(f"📊 Graphiques basés sur {len(df_all)} éléments (toutes les données)")
            
            # Graphiques spécifiques selon l'endpoint
            if st.session_state.selected_endpoint == "events":
                # Graphique 1: Nombre d'events par unit
                if 'organizational_unit_id' in df_all.columns:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Nombre d'événements par unité")
                        # Utiliser les noms déjà ajoutés
                        unit_counts = df_all['unit_name'].value_counts().reset_index()
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
                if 'type' in df_all.columns:
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        st.markdown("#### Types d'événements")
                        type_counts = df_all['type'].value_counts().reset_index()
                        type_counts.columns = ['Type', 'Nombre']
                        
                        fig3 = px.bar(type_counts, x='Type', y='Nombre',
                                     title='Répartition par type d\'événement')
                        st.plotly_chart(fig3, use_container_width=True)
                    
                    with col4:
                        st.markdown("#### Classification des événements")
                        if 'classification' in df_all.columns:
                            class_counts = df_all['classification'].value_counts().reset_index()
                            class_counts.columns = ['Classification', 'Nombre']
                            
                            fig4 = px.pie(class_counts, values='Nombre', names='Classification',
                                         title='Distribution par classification')
                            st.plotly_chart(fig4, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "persons":
                pass
                # Graphiques pour les personnes
                # if 'role' in df.columns:
                #     col1, col2 = st.columns(2)
                    
                #     with col1:
                #         st.markdown("#### Répartition par rôle")
                #         role_counts = df['role'].value_counts().reset_index()
                #         role_counts.columns = ['Rôle', 'Nombre']
                        
                #         fig1 = px.pie(role_counts, values='Nombre', names='Rôle',
                #                      title='Distribution des personnes par rôle')
                #         st.plotly_chart(fig1, use_container_width=True)
                    
                #     with col2:
                #         st.markdown("#### Nombre de personnes par rôle")
                #         fig2 = px.bar(role_counts, x='Rôle', y='Nombre',
                #                      title='Effectif par rôle')
                #         st.plotly_chart(fig2, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "measures":
                # Graphiques pour les mesures correctives
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'organizational_unit_id' in df_all.columns:
                        st.markdown("#### Mesures par unité")
                        # Utiliser les noms déjà ajoutés
                        unit_counts = df_all['unit_name'].value_counts().reset_index()
                        unit_counts.columns = ['Unité', 'Nombre']
                        
                        fig1 = px.bar(unit_counts.head(10), x='Unité', y='Nombre',
                                     title='Top 10 des unités avec le plus de mesures')
                        fig1.update_xaxes(tickangle=-45)
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    if 'cost' in df_all.columns:
                        st.markdown("#### Distribution des coûts")
                        df_cost = df_all[df_all['cost'].notna()]
                        if len(df_cost) > 0:
                            fig2 = px.histogram(df_cost, x='cost', nbins=20,
                                              title='Distribution des coûts des mesures')
                            st.plotly_chart(fig2, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "risks":
                # Graphiques pour les risques
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'gravity' in df_all.columns:
                        st.markdown("#### Gravité des risques")
                        gravity_counts = df_all['gravity'].value_counts().reset_index()
                        gravity_counts.columns = ['Gravité', 'Nombre']
                        
                        fig1 = px.pie(gravity_counts, values='Nombre', names='Gravité',
                                     title='Distribution par gravité')
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    if 'probability' in df_all.columns:
                        st.markdown("#### Probabilité des risques")
                        prob_counts = df_all['probability'].value_counts().reset_index()
                        prob_counts.columns = ['Probabilité', 'Nombre']
                        
                        fig2 = px.bar(prob_counts, x='Probabilité', y='Nombre',
                                     title='Répartition par probabilité')
                        st.plotly_chart(fig2, use_container_width=True)
            
            elif st.session_state.selected_endpoint == "units":
                pass
                # # Graphiques pour les unités
                # if 'location' in df.columns:
                #     st.markdown("#### Unités par localisation")
                #     location_counts = df['location'].value_counts().reset_index()
                #     location_counts.columns = ['Localisation', 'Nombre']
                    
                #     fig1 = px.bar(location_counts, x='Localisation', y='Nombre',
                #                  title='Nombre d\'unités par localisation')
                #     st.plotly_chart(fig1, use_container_width=True)
            
            # === CRÉATEUR DE GRAPHIQUES PERSONNALISÉS ===
            st.markdown("---")
            st.subheader("🎨 Créateur de graphiques personnalisés")
            
            st.info(f"ℹ️ Les graphiques personnalisés utilisent l'ensemble complet des données ({len(df_all)} éléments)")
            
            # Utiliser df_all pour les graphiques personnalisés
            df_custom = df_all.copy()
            
            # Obtenir les colonnes disponibles
            available_columns = list(df_custom.columns)
            numeric_columns = list(df_custom.select_dtypes(include=[np.number]).columns)
            categorical_columns = list(df_custom.select_dtypes(include=['object', 'category', 'bool']).columns)
            
            col_config1, col_config2 = st.columns(2)
            
            # Initialiser toutes les variables à None
            x_axis = None
            y_axis = None
            color_column = None
            size_column = None
            names_column = None
            values_column = None
            path_columns = None
            
            with col_config1:
                # Type de graphique
                chart_type = st.selectbox(
                    "Type de graphique",
                    ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram", 
                     "Box Plot", "Violin Plot", "Heatmap", "Area Chart", "Sunburst"],
                    help="Sélectionnez le type de visualisation"
                )
                
                # Axe X
                if chart_type not in ["Pie Chart", "Histogram", "Sunburst"]:
                    x_axis = st.selectbox(
                        "Axe X",
                        available_columns,
                        help="Choisissez la colonne pour l'axe X"
                    )
                
                # Axe Y
                if chart_type not in ["Pie Chart", "Sunburst"]:
                    if chart_type == "Histogram":
                        y_axis = st.selectbox(
                            "Valeur à analyser",
                            numeric_columns if numeric_columns else available_columns,
                            help="Choisissez la colonne pour l'histogramme"
                        )
                    else:
                        y_axis = st.selectbox(
                            "Axe Y",
                            available_columns,
                            help="Choisissez la colonne pour l'axe Y"
                        )
            
            with col_config2:
                # Couleur
                use_color = st.checkbox("Utiliser une colonne pour les couleurs", value=False)
                if use_color:
                    color_column = st.selectbox(
                        "Colonne de couleur",
                        [None] + available_columns,
                        help="Sélectionnez une colonne pour différencier par couleur"
                    )
                
                # Taille (pour scatter plot)
                if chart_type == "Scatter Plot":
                    use_size = st.checkbox("Utiliser une colonne pour la taille", value=False)
                    if use_size:
                        size_column = st.selectbox(
                            "Colonne de taille",
                            [None] + numeric_columns,
                            help="Sélectionnez une colonne numérique pour la taille des points"
                        )
                
                # Options pour Pie Chart et Sunburst
                if chart_type in ["Pie Chart", "Sunburst"]:
                    names_column = st.selectbox(
                        "Catégories (noms)",
                        categorical_columns if categorical_columns else available_columns,
                        help="Choisissez la colonne pour les catégories"
                    )
                    values_column = st.selectbox(
                        "Valeurs (optionnel)",
                        [None] + (numeric_columns if numeric_columns else available_columns),
                        help="Choisissez la colonne pour les valeurs (laisser vide pour compter les occurrences)"
                    )
                    if chart_type == "Sunburst":
                        use_path = st.checkbox("Utiliser une hiérarchie", value=False)
                        if use_path:
                            path_columns = st.multiselect(
                                "Colonnes hiérarchiques (ordre important)",
                                available_columns,
                                help="Sélectionnez les colonnes dans l'ordre hiérarchique"
                            )
            
            # Options supplémentaires
            col_opt1, col_opt2, col_opt3 = st.columns(3)
            with col_opt1:
                chart_title = st.text_input("Titre du graphique", value=f"{chart_type} personnalisé")
            with col_opt2:
                if chart_type in ["Bar Chart", "Line Chart", "Area Chart"]:
                    aggregation = st.selectbox(
                        "Agrégation",
                        ["Aucune", "Somme", "Moyenne", "Compte", "Min", "Max"],
                        help="Comment agréger les données"
                    )
                else:
                    aggregation = "Aucune"
            with col_opt3:
                chart_height = st.slider("Hauteur du graphique", 300, 800, 500, 50)
            
            # Bouton pour générer le graphique
            if st.button("Générer le graphique", type="primary", use_container_width=True):
                try:
                    df_plot = df_custom.copy()
                    
                    # Créer le graphique selon le type
                    if chart_type == "Bar Chart":
                        if not x_axis or not y_axis:
                            st.error("⚠️ Veuillez sélectionner les axes X et Y pour créer un graphique en barres.")
                        else:
                            if aggregation != "Aucune" and x_axis and y_axis:
                                if aggregation == "Somme":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].sum().reset_index()
                                elif aggregation == "Moyenne":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].mean().reset_index()
                                elif aggregation == "Compte":
                                    df_plot = df_plot.groupby(x_axis).size().reset_index(name=y_axis)
                                elif aggregation == "Min":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].min().reset_index()
                                elif aggregation == "Max":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].max().reset_index()
                            
                            fig = px.bar(df_plot, x=x_axis, y=y_axis, color=color_column, 
                                        title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Line Chart":
                        if not x_axis or not y_axis:
                            st.error("⚠️ Veuillez sélectionner les axes X et Y pour créer un graphique linéaire.")
                        else:
                            if aggregation != "Aucune" and x_axis and y_axis:
                                if aggregation == "Somme":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].sum().reset_index()
                                elif aggregation == "Moyenne":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].mean().reset_index()
                                elif aggregation == "Compte":
                                    df_plot = df_plot.groupby(x_axis).size().reset_index(name=y_axis)
                            
                            fig = px.line(df_plot, x=x_axis, y=y_axis, color=color_column,
                                         title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Scatter Plot":
                        if not x_axis or not y_axis:
                            st.error("⚠️ Veuillez sélectionner les axes X et Y pour créer un nuage de points.")
                        else:
                            fig = px.scatter(df_plot, x=x_axis, y=y_axis, color=color_column,
                                           size=size_column, title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Pie Chart":
                        if not names_column:
                            st.error("⚠️ Veuillez sélectionner une colonne pour les catégories.")
                        else:
                            if values_column:
                                fig = px.pie(df_plot, names=names_column, values=values_column,
                                           title=chart_title, height=chart_height)
                            else:
                                # Compter les occurrences
                                df_counts = df_plot[names_column].value_counts().reset_index()
                                df_counts.columns = [names_column, 'count']
                                fig = px.pie(df_counts, names=names_column, values='count',
                                           title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Histogram":
                        if not y_axis:
                            st.error("⚠️ Veuillez sélectionner une valeur à analyser pour créer un histogramme.")
                        else:
                            fig = px.histogram(df_plot, x=y_axis, color=color_column,
                                             title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Box Plot":
                        if not y_axis:
                            st.error("⚠️ Veuillez sélectionner au moins l'axe Y pour créer un box plot.")
                        else:
                            fig = px.box(df_plot, x=x_axis, y=y_axis, color=color_column,
                                        title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Violin Plot":
                        if not y_axis:
                            st.error("⚠️ Veuillez sélectionner au moins l'axe Y pour créer un violin plot.")
                        else:
                            fig = px.violin(df_plot, x=x_axis, y=y_axis, color=color_column,
                                          title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Heatmap":
                        if len(numeric_columns) < 1:
                            st.error("⚠️ Aucune colonne numérique disponible pour créer une heatmap.")
                        else:
                            # Pour heatmap, on utilise les colonnes numériques
                            numeric_df = df_plot[numeric_columns].corr() if len(numeric_columns) > 1 else df_plot[numeric_columns]
                            fig = px.imshow(numeric_df, title=chart_title, height=chart_height,
                                          labels=dict(color="Valeur"))
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Area Chart":
                        if not x_axis or not y_axis:
                            st.error("⚠️ Veuillez sélectionner les axes X et Y pour créer un graphique en aires.")
                        else:
                            if aggregation != "Aucune" and x_axis and y_axis:
                                if aggregation == "Somme":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].sum().reset_index()
                                elif aggregation == "Moyenne":
                                    df_plot = df_plot.groupby(x_axis)[y_axis].mean().reset_index()
                            
                            fig = px.area(df_plot, x=x_axis, y=y_axis, color=color_column,
                                        title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Sunburst":
                        if not names_column:
                            st.error("⚠️ Veuillez sélectionner une colonne pour les catégories.")
                        else:
                            if path_columns and len(path_columns) > 0:
                                fig = px.sunburst(df_plot, path=path_columns, values=values_column if values_column else None,
                                                title=chart_title, height=chart_height)
                            else:
                                # Utiliser une seule colonne
                                if values_column:
                                    fig = px.sunburst(df_plot, path=[names_column], values=values_column,
                                                    title=chart_title, height=chart_height)
                                else:
                                    df_counts = df_plot[names_column].value_counts().reset_index()
                                    df_counts.columns = [names_column, 'count']
                                    fig = px.sunburst(df_counts, path=[names_column], values='count',
                                                    title=chart_title, height=chart_height)
                            st.plotly_chart(fig, use_container_width=True)
                    
                    # Option pour télécharger les données utilisées
                    st.download_button(
                        label="📥 Télécharger les données du graphique (CSV)",
                        data=df_plot.to_csv(index=False).encode('utf-8'),
                        file_name=f"{chart_type.lower().replace(' ', '_')}_data.csv",
                        mime="text/csv"
                    )
                    
                except Exception as e:
                    st.error(f"Erreur lors de la création du graphique: {str(e)}")
                    st.info("Assurez-vous que les colonnes sélectionnées sont compatibles avec le type de graphique choisi.")
            
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
