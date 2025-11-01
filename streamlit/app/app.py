import requests
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Configuration de la page
st.set_page_config(page_title="Events Safety API Dashboard", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS pour un meilleur design
st.markdown("""
<style>
    /* Style général */
    .main {
        padding: 0rem 1rem;
        color: #ffffff;
    }
    
    /* Tous les textes en blanc */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #ffffff !important;
    }
    
    /* Cards pour les événements */
    .event-card {
        background: linear-gradient(135deg, #f6f8fb 0%, #ffffff 100%);
        padding: 1.2rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        margin-bottom: 1rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }
    
    .event-card:hover {
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
        border-color: #3b82f6;
    }
    
    .event-card-danger {
        background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
        border-color: #fecaca;
    }
    
    .event-card-danger:hover {
        border-color: #ef4444;
    }
    
    .event-card-warning {
        background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
        border-color: #fed7aa;
    }
    
    .event-card-warning:hover {
        border-color: #f59e0b;
    }
    
    .event-card h4 {
        margin: 0 0 0.75rem 0;
        font-size: 1rem;
        font-weight: 600;
        color: #1f2937 !important;
    }
    
    .event-card p {
        margin: 0.4rem 0;
        color: #6b7280 !important;
        font-size: 0.85rem;
    }
    
    .event-card .event-desc {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid #e5e7eb;
        color: #4b5563 !important;
        line-height: 1.5;
        font-size: 0.85rem;
    }
    
    /* Métriques */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    
    /* Titres de sections */
    .section-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        color: #ffffff !important;
    }
    
    /* Navigation améliorée */
    div[data-testid="stHorizontalBlock"] button {
        border-radius: 8px !important;
        font-weight: 500;
    }
    
    /* Streamlit elements en blanc */
    .stMarkdown, .stText {
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

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
if 'total_count' not in st.session_state:
    st.session_state.total_count = 0

# Titre principal avec style
st.markdown("<h1 style='text-align: center; color: #ffffff; margin-bottom: 2rem;'>Events Safety Dashboard</h1>", unsafe_allow_html=True)

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
        
        # Charger toutes les données pour obtenir le count total
        if st.session_state.total_count == 0:
            all_data_initial = get_all_data(url_api)
            st.session_state.total_count = len(all_data_initial)
        
        # Ajouter les nouveaux items à la liste existante SANS DUPLICATION
        if items:
            # Créer un set des IDs déjà présents pour éviter les doublons
            existing_ids = set()
            id_field = None
            
            # Déterminer le champ ID selon l'endpoint
            if st.session_state.selected_endpoint == "events" and len(st.session_state.all_items) > 0:
                id_field = 'event_id'
            elif st.session_state.selected_endpoint == "persons" and len(st.session_state.all_items) > 0:
                id_field = 'person_id'
            elif st.session_state.selected_endpoint == "units" and len(st.session_state.all_items) > 0:
                id_field = 'unit_id'
            elif st.session_state.selected_endpoint == "measures" and len(st.session_state.all_items) > 0:
                id_field = 'measure_id'
            elif st.session_state.selected_endpoint == "risks" and len(st.session_state.all_items) > 0:
                id_field = 'risk_id'
            
            if id_field and id_field in items[0]:
                existing_ids = {item[id_field] for item in st.session_state.all_items if id_field in item}
                # Ajouter seulement les nouveaux items
                new_items = [item for item in items if item.get(id_field) not in existing_ids]
                st.session_state.all_items.extend(new_items)
            else:
                # Pas de champ ID trouvé, ajouter tous les items
                st.session_state.all_items.extend(items)
        
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
            
            # Charger TOUTES les données pour les graphiques et stats
            with st.spinner("Chargement des données..."):
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
                
                # Parser les dates dans df_all
                if 'start_datetime' in df_all.columns:
                    df_all['start_datetime'] = pd.to_datetime(df_all['start_datetime'], errors='coerce')
            
            # === MÉTRIQUE EN HAUT ===
            st.markdown("<br>", unsafe_allow_html=True)
            
            # === GRAPHIQUES EN HAUT ===
            st.markdown("<div class='section-title'>Visualisations</div>", unsafe_allow_html=True)
            
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
            
            # Graphiques pour EVENTS
            st.markdown("### Événements")
            st.markdown(f"<p style='color: #ffffff; font-size: 0.85rem; margin-top: -0.5rem; margin-bottom: 1rem;'>{len(df_all):,} événements au total</p>", unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Nombre d'événements par unité")
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
            
            # Graphiques pour MEASURES
            st.markdown("### Mesures correctives")
            
            # Charger les données des mesures
            measures_url = f"{BASE_URL}/measures/"
            measures_data = get_all_data(measures_url)
            if measures_data:
                df_measures = pd.DataFrame(measures_data)
                st.markdown(f"<p style='color: #ffffff; font-size: 0.85rem; margin-top: -0.5rem; margin-bottom: 1rem;'>{len(df_measures):,} mesures correctives au total</p>", unsafe_allow_html=True)
                if 'organizational_unit_id' in df_measures.columns:
                    df_measures['unit_name'] = df_measures['organizational_unit_id'].map(
                        lambda x: units_map.get(x, f"Unit {x}") if pd.notna(x) else None
                    )
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### Mesures par unité")
                    unit_counts = df_measures['unit_name'].value_counts().reset_index()
                    unit_counts.columns = ['Unité', 'Nombre']
                    
                    fig1 = px.bar(unit_counts.head(10), x='Unité', y='Nombre',
                                 title='Top 10 des unités avec le plus de mesures')
                    fig1.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    if 'cost' in df_measures.columns:
                        st.markdown("#### Distribution des coûts")
                        df_cost = df_measures[df_measures['cost'].notna()]
                        if len(df_cost) > 0:
                            fig2 = px.histogram(df_cost, x='cost', nbins=20,
                                              title='Distribution des coûts des mesures')
                            st.plotly_chart(fig2, use_container_width=True)
            
            # Graphiques pour RISKS
            st.markdown("### Risques")
            
            # Charger les données des risques
            risks_url = f"{BASE_URL}/risks/"
            risks_data = get_all_data(risks_url)
            if risks_data:
                df_risks = pd.DataFrame(risks_data)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'gravity' in df_risks.columns:
                        st.markdown("#### Gravité des risques")
                        gravity_counts = df_risks['gravity'].value_counts().reset_index()
                        gravity_counts.columns = ['Gravité', 'Nombre']
                        
                        fig1 = px.pie(gravity_counts, values='Nombre', names='Gravité',
                                     title='Distribution par gravité')
                        st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    if 'probability' in df_risks.columns:
                        st.markdown("#### Probabilité des risques")
                        prob_counts = df_risks['probability'].value_counts().reset_index()
                        prob_counts.columns = ['Probabilité', 'Nombre']
                        
                        fig2 = px.bar(prob_counts, x='Probabilité', y='Nombre',
                                     title='Répartition par probabilité')
                        st.plotly_chart(fig2, use_container_width=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # === 3 DERNIERS ÉVÉNEMENTS ===
            if len(df_all) > 0:
                st.markdown("<div class='section-title'>Derniers événements</div>", unsafe_allow_html=True)
                
                # Trier par extracted_date (plus récent en premier)
                if 'extracted_date' in df_all.columns:
                    df_recent = df_all.copy()
                    df_recent['extracted_date'] = pd.to_datetime(df_recent['extracted_date'], errors='coerce')
                    df_recent = df_recent.sort_values('extracted_date', ascending=False).head(3)
                    
                    # Créer 3 colonnes pour les 3 derniers événements
                    event_cols = st.columns(3)
                    
                    for idx, (i, event) in enumerate(df_recent.iterrows()):
                        with event_cols[idx]:
                            # Déterminer la classe CSS selon la classification
                            classification = str(event.get('classification', '')).lower()
                            if 'danger' in classification or 'critical' in classification or 'grave' in classification:
                                card_class = 'event-card-danger'
                            elif 'warn' in classification or 'moyen' in classification:
                                card_class = 'event-card-warning'
                            else:
                                card_class = 'event-card'
                            
                            # Extraire les informations
                            event_type = event.get('type', 'N/A')
                            event_date = event.get('extracted_date')
                            if pd.notna(event_date):
                                event_date = pd.to_datetime(event_date).strftime('%d/%m/%Y')
                            else:
                                event_date = 'N/A'
                            event_unit = event.get('unit_name', f"Unit {event.get('organizational_unit_id', 'N/A')}")
                            event_class = event.get('classification', 'N/A')
                            event_desc = event.get('description', 'Aucune description')
                            if len(str(event_desc)) > 150:
                                event_desc = str(event_desc)[:150] + '...'
                            
                            # Créer la card HTML
                            st.markdown(f"""
                            <div class='{card_class}'>
                                <h4>{event_type}</h4>
                                <p><strong>Date:</strong> {event_date}</p>
                                <p><strong>Unité:</strong> {event_unit}</p>
                                <p><strong>Classification:</strong> {event_class}</p>
                                <p class='event-desc'>{event_desc}</p>
                            </div>
                            """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # === CRÉATEUR DE GRAPHIQUES PERSONNALISÉS ===
            st.markdown("---")
            st.subheader("Créateur de graphiques personnalisés")
            
            # Sélecteur de table source
            st.markdown("**Sélectionner la source des données**")
            source_endpoint = st.selectbox(
                "Table source",
                list(ENDPOINTS.keys()),
                index=list(ENDPOINTS.keys()).index(st.session_state.selected_endpoint),
                key="custom_chart_source",
                help="Choisissez la table dont vous souhaitez utiliser les données"
            )
            
            # Charger les données de la table sélectionnée
            source_url = f"{BASE_URL}{ENDPOINTS[source_endpoint]}"
            source_data = get_all_data(source_url)
            
            if source_data:
                df_custom = pd.DataFrame(source_data)
                
                # Ajouter les noms lisibles pour les IDs dans df_custom
                if 'organizational_unit_id' in df_custom.columns:
                    df_custom['unit_name'] = df_custom['organizational_unit_id'].map(
                        lambda x: units_map.get(x, f"Unit {x}") if pd.notna(x) else None
                    )
                
                if 'declared_by_id' in df_custom.columns:
                    df_custom['declared_by_name'] = df_custom['declared_by_id'].map(
                        lambda x: persons_map.get(x, f"Person {x}") if pd.notna(x) else None
                    )
                
                if 'owner_id' in df_custom.columns:
                    df_custom['owner_name'] = df_custom['owner_id'].map(
                        lambda x: persons_map.get(x, f"Person {x}") if pd.notna(x) else None
                    )
                
                st.info(f"Utilisation de {len(df_custom):,} éléments de la table '{source_endpoint}'")
            
            # Obtenir les colonnes disponibles
            available_columns = list(df_custom.columns)
            numeric_columns = list(df_custom.select_dtypes(include=[np.number]).columns)
            categorical_columns = list(df_custom.select_dtypes(include=['object', 'category', 'bool']).columns)
            
            # Filtrer les colonnes avec trop de valeurs uniques (probablement des IDs)
            good_categorical_columns = []
            for col in categorical_columns:
                unique_count = df_custom[col].nunique()
                if unique_count <= 50:  # Limite raisonnable pour des catégories
                    good_categorical_columns.append(col)
            
            col_config1, col_config2 = st.columns(2)
            
            # Initialiser toutes les variables à None
            x_axis = None
            y_axis = None
            color_column = None
            size_column = None
            names_column = None
            values_column = None
            path_columns = None
            validation_errors = []
            
            with col_config1:
                # Type de graphique
                chart_type = st.selectbox(
                    "Type de graphique",
                    ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram", 
                     "Box Plot", "Violin Plot", "Heatmap", "Area Chart", "Sunburst"],
                    help="Sélectionnez le type de visualisation"
                )
                
                # Messages d'aide selon le type de graphique
                chart_requirements = {
                    "Bar Chart": "📊 Recommandé: X = catégorie, Y = valeur numérique",
                    "Line Chart": "📈 Recommandé: X = temps/ordre, Y = valeur numérique",
                    "Scatter Plot": "🔵 Nécessite: X et Y numériques pour analyser les corrélations",
                    "Pie Chart": "🥧 Nécessite: Catégories (max 15 pour la lisibilité)",
                    "Histogram": "📊 Nécessite: Une colonne numérique pour la distribution",
                    "Box Plot": "📦 Nécessite: Y numérique (X catégorique optionnel)",
                    "Violin Plot": "🎻 Nécessite: Y numérique (X catégorique optionnel)",
                    "Heatmap": "🔥 Analyse la corrélation entre colonnes numériques",
                    "Area Chart": "📈 Recommandé: X = temps/ordre, Y = valeur numérique",
                    "Sunburst": "☀️ Nécessite: Catégories hiérarchiques"
                }
                st.info(chart_requirements[chart_type])
                
                # Axe X avec filtrage intelligent selon le type de graphique
                if chart_type not in ["Pie Chart", "Histogram", "Sunburst"]:
                    if chart_type == "Scatter Plot":
                        # Pour scatter, on recommande du numérique
                        x_options = numeric_columns if numeric_columns else available_columns
                        x_axis = st.selectbox(
                            "Axe X (numérique recommandé)",
                            x_options,
                            help="Choisissez une colonne numérique pour l'axe X"
                        )
                    elif chart_type in ["Bar Chart", "Box Plot", "Violin Plot"]:
                        # Pour bar/box/violin, on recommande du catégoriel
                        x_options = good_categorical_columns if good_categorical_columns else available_columns
                        x_axis = st.selectbox(
                            "Axe X (catégorie recommandée)",
                            x_options,
                            help="Choisissez une colonne catégorielle pour l'axe X"
                        )
                    else:
                        # Line et Area acceptent les deux
                        x_axis = st.selectbox(
                            "Axe X",
                            available_columns,
                            help="Choisissez la colonne pour l'axe X"
                        )
                
                # Axe Y avec filtrage intelligent
                if chart_type not in ["Pie Chart", "Sunburst"]:
                    if chart_type == "Histogram":
                        if not numeric_columns:
                            st.warning("⚠️ Aucune colonne numérique disponible pour un histogramme")
                            validation_errors.append("Histogramme nécessite une colonne numérique")
                        y_axis = st.selectbox(
                            "Valeur à analyser (numérique)",
                            numeric_columns if numeric_columns else available_columns,
                            help="Choisissez la colonne numérique pour l'histogramme"
                        )
                    elif chart_type in ["Scatter Plot", "Box Plot", "Violin Plot", "Line Chart", "Bar Chart", "Area Chart"]:
                        # Ces graphiques nécessitent Y numérique
                        if not numeric_columns:
                            st.warning("⚠️ Aucune colonne numérique disponible pour l'axe Y")
                            validation_errors.append(f"{chart_type} nécessite une colonne numérique pour Y")
                        y_axis = st.selectbox(
                            "Axe Y (numérique recommandé)",
                            numeric_columns if numeric_columns else available_columns,
                            help="Choisissez une colonne numérique pour l'axe Y"
                        )
                    else:
                        y_axis = st.selectbox(
                            "Axe Y",
                            available_columns,
                            help="Choisissez la colonne pour l'axe Y"
                        )
            
            with col_config2:
                # Couleur - seulement pour colonnes catégorielles valides
                use_color = st.checkbox("Utiliser une colonne pour les couleurs", value=False)
                if use_color:
                    color_options = good_categorical_columns if good_categorical_columns else categorical_columns
                    if color_options:
                        color_column = st.selectbox(
                            "Colonne de couleur (catégories limitées)",
                            [None] + color_options,
                            help="Sélectionnez une colonne catégorielle (max 50 valeurs uniques)"
                        )
                    else:
                        st.warning("Aucune colonne catégorielle appropriée trouvée")
                
                # Taille (pour scatter plot)
                if chart_type == "Scatter Plot":
                    use_size = st.checkbox("Utiliser une colonne pour la taille", value=False)
                    if use_size:
                        if not numeric_columns:
                            st.warning("⚠️ Aucune colonne numérique disponible pour la taille")
                        size_column = st.selectbox(
                            "Colonne de taille (numérique)",
                            [None] + numeric_columns,
                            help="Sélectionnez une colonne numérique pour la taille des points"
                        )
                
                # Options pour Pie Chart et Sunburst
                if chart_type in ["Pie Chart", "Sunburst"]:
                    if not good_categorical_columns:
                        st.error("❌ Aucune colonne catégorielle appropriée trouvée pour ce type de graphique")
                        validation_errors.append("Pie/Sunburst nécessite des colonnes catégorielles avec moins de 50 valeurs")
                    else:
                        names_column = st.selectbox(
                            "Catégories (noms)",
                            good_categorical_columns,
                            help="Choisissez la colonne pour les catégories (max 15 recommandé)"
                        )
                        
                        # Vérifier le nombre de catégories
                        if names_column:
                            n_categories = df_custom[names_column].nunique()
                            if n_categories > 15:
                                st.warning(f"⚠️ {n_categories} catégories détectées. Plus de 15 catégories rendent le graphique difficile à lire.")
                            elif n_categories < 2:
                                st.error("❌ Au moins 2 catégories sont nécessaires")
                                validation_errors.append("Insuffisant de catégories")
                        
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
                                    good_categorical_columns,
                                    help="Sélectionnez 2-4 colonnes dans l'ordre hiérarchique"
                                )
                                if path_columns and len(path_columns) > 4:
                                    st.warning("⚠️ Plus de 4 niveaux hiérarchiques rendent le graphique complexe")
            
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
                    if aggregation != "Aucune" and y_axis and y_axis not in numeric_columns and aggregation in ["Somme", "Moyenne", "Min", "Max"]:
                        st.warning(f"⚠️ L'agrégation '{aggregation}' nécessite une colonne Y numérique")
                else:
                    aggregation = "Aucune"
            with col_opt3:
                chart_height = st.slider("Hauteur du graphique", 300, 800, 500, 50)
            
            # Afficher les erreurs de validation
            if validation_errors:
                st.error("⚠️ **Problèmes détectés:**")
                for error in validation_errors:
                    st.error(f"  • {error}")
            
            # Validation finale avant d'activer le bouton
            can_generate = True
            validation_message = ""
            
            if chart_type == "Scatter Plot":
                if x_axis and y_axis:
                    if x_axis not in numeric_columns or y_axis not in numeric_columns:
                        can_generate = False
                        validation_message = "⚠️ Scatter Plot nécessite X et Y numériques"
                elif not x_axis or not y_axis:
                    can_generate = False
                    validation_message = "⚠️ Veuillez sélectionner X et Y"
            
            elif chart_type == "Heatmap":
                if len(numeric_columns) < 2:
                    can_generate = False
                    validation_message = "⚠️ Heatmap nécessite au moins 2 colonnes numériques"
            
            elif chart_type in ["Pie Chart", "Sunburst"]:
                if not names_column:
                    can_generate = False
                    validation_message = "⚠️ Veuillez sélectionner une colonne de catégories"
                elif names_column and df_custom[names_column].nunique() > 30:
                    can_generate = False
                    validation_message = f"❌ Trop de catégories ({df_custom[names_column].nunique()}). Maximum recommandé: 30"
            
            elif chart_type == "Histogram":
                if not y_axis or y_axis not in numeric_columns:
                    can_generate = False
                    validation_message = "⚠️ Histogramme nécessite une colonne numérique"
            
            elif chart_type in ["Bar Chart", "Line Chart", "Area Chart", "Box Plot", "Violin Plot"]:
                if not y_axis:
                    can_generate = False
                    validation_message = "⚠️ Veuillez sélectionner l'axe Y"
            
            if validation_message:
                st.warning(validation_message)
            
            # Bouton pour générer le graphique
            button_disabled = not can_generate
            if st.button("Générer le graphique", type="primary", use_container_width=True, disabled=button_disabled):
                try:
                    df_plot = df_custom.copy()
                    
                    # Validation supplémentaire: vérifier les données
                    if len(df_plot) < 2:
                        st.error("❌ Pas assez de données (minimum 2 lignes)")
                        st.stop()
                    
                    # Créer le graphique selon le type
                    if chart_type == "Bar Chart":
                        # Nettoyer les données
                        df_plot = df_plot.dropna(subset=[x_axis, y_axis])
                        
                        if len(df_plot) == 0:
                            st.error("❌ Aucune donnée valide après nettoyage")
                            st.stop()
                        
                        # Limiter le nombre de catégories pour éviter les graphiques surchargés
                        if df_plot[x_axis].nunique() > 50:
                            st.warning(f"⚠️ Trop de catégories ({df_plot[x_axis].nunique()}). Affichage des 30 premières.")
                            top_categories = df_plot[x_axis].value_counts().head(30).index
                            df_plot = df_plot[df_plot[x_axis].isin(top_categories)]
                        
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
                        df_plot = df_plot.dropna(subset=[x_axis, y_axis])
                        
                        if len(df_plot) == 0:
                            st.error("❌ Aucune donnée valide après nettoyage")
                            st.stop()
                        
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
                        df_plot = df_plot.dropna(subset=[x_axis, y_axis])
                        
                        if len(df_plot) < 2:
                            st.error("❌ Au moins 2 points sont nécessaires pour un scatter plot")
                            st.stop()
                        
                        # Limiter le nombre de points pour les performances
                        if len(df_plot) > 5000:
                            st.info(f"ℹ️ Échantillonnage de 5000 points sur {len(df_plot)} pour les performances")
                            df_plot = df_plot.sample(n=5000, random_state=42)
                        
                        fig = px.scatter(df_plot, x=x_axis, y=y_axis, color=color_column,
                                       size=size_column, title=chart_title, height=chart_height)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Pie Chart":
                        if values_column:
                            df_plot = df_plot.dropna(subset=[names_column, values_column])
                            # Limiter à 15 catégories max
                            if df_plot[names_column].nunique() > 15:
                                st.info("ℹ️ Affichage des 15 catégories principales")
                                top_cats = df_plot.groupby(names_column)[values_column].sum().nlargest(15).index
                                df_plot = df_plot[df_plot[names_column].isin(top_cats)]
                            fig = px.pie(df_plot, names=names_column, values=values_column,
                                       title=chart_title, height=chart_height)
                        else:
                            # Compter les occurrences
                            df_counts = df_plot[names_column].value_counts().reset_index()
                            df_counts.columns = [names_column, 'count']
                            # Limiter à 15 catégories
                            if len(df_counts) > 15:
                                st.info("ℹ️ Affichage des 15 catégories principales")
                                df_counts = df_counts.head(15)
                            fig = px.pie(df_counts, names=names_column, values='count',
                                       title=chart_title, height=chart_height)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Histogram":
                        df_plot = df_plot.dropna(subset=[y_axis])
                        
                        if len(df_plot) == 0:
                            st.error("❌ Aucune donnée valide après nettoyage")
                            st.stop()
                        
                        fig = px.histogram(df_plot, x=y_axis, color=color_column,
                                         title=chart_title, height=chart_height, nbins=30)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Box Plot":
                        df_plot = df_plot.dropna(subset=[y_axis])
                        
                        if len(df_plot) == 0:
                            st.error("❌ Aucune donnée valide après nettoyage")
                            st.stop()
                        
                        fig = px.box(df_plot, x=x_axis, y=y_axis, color=color_column,
                                    title=chart_title, height=chart_height)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Violin Plot":
                        df_plot = df_plot.dropna(subset=[y_axis])
                        
                        if len(df_plot) == 0:
                            st.error("❌ Aucune donnée valide après nettoyage")
                            st.stop()
                        
                        fig = px.violin(df_plot, x=x_axis, y=y_axis, color=color_column,
                                      title=chart_title, height=chart_height)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Heatmap":
                        # Limiter aux colonnes numériques pertinentes (max 20)
                        numeric_cols_for_heatmap = numeric_columns[:20] if len(numeric_columns) > 20 else numeric_columns
                        if len(numeric_columns) > 20:
                            st.info(f"ℹ️ Utilisation de 20 colonnes numériques sur {len(numeric_columns)} pour la lisibilité")
                        
                        numeric_df = df_plot[numeric_cols_for_heatmap].corr()
                        fig = px.imshow(numeric_df, title=chart_title, height=chart_height,
                                      labels=dict(color="Corrélation"), 
                                      color_continuous_scale="RdBu_r",
                                      aspect="auto")
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Area Chart":
                        df_plot = df_plot.dropna(subset=[x_axis, y_axis])
                        
                        if len(df_plot) == 0:
                            st.error("❌ Aucune donnée valide après nettoyage")
                            st.stop()
                        
                        if aggregation != "Aucune" and x_axis and y_axis:
                            if aggregation == "Somme":
                                df_plot = df_plot.groupby(x_axis)[y_axis].sum().reset_index()
                            elif aggregation == "Moyenne":
                                df_plot = df_plot.groupby(x_axis)[y_axis].mean().reset_index()
                        
                        fig = px.area(df_plot, x=x_axis, y=y_axis, color=color_column,
                                    title=chart_title, height=chart_height)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    elif chart_type == "Sunburst":
                        if path_columns and len(path_columns) > 0:
                            # Limiter le nombre de lignes pour éviter les graphiques trop complexes
                            if len(df_plot) > 1000:
                                st.info("ℹ️ Échantillonnage de 1000 lignes pour la lisibilité")
                                df_plot = df_plot.sample(n=1000, random_state=42)
                            
                            df_plot = df_plot.dropna(subset=path_columns)
                            
                            if len(df_plot) == 0:
                                st.error("❌ Aucune donnée valide après nettoyage")
                                st.stop()
                            
                            fig = px.sunburst(df_plot, path=path_columns, values=values_column if values_column else None,
                                            title=chart_title, height=chart_height)
                        else:
                            # Utiliser une seule colonne
                            df_counts = df_plot[names_column].value_counts().reset_index()
                            df_counts.columns = [names_column, 'count']
                            # Limiter à 20 catégories
                            if len(df_counts) > 20:
                                st.info("ℹ️ Affichage des 20 catégories principales")
                                df_counts = df_counts.head(20)
                            
                            if values_column:
                                df_plot_clean = df_plot.dropna(subset=[names_column, values_column])
                                fig = px.sunburst(df_plot_clean, path=[names_column], values=values_column,
                                                title=chart_title, height=chart_height)
                            else:
                                fig = px.sunburst(df_counts, path=[names_column], values='count',
                                                title=chart_title, height=chart_height)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Afficher des statistiques sur le graphique généré
                    st.success(f"✅ Graphique généré avec succès ({len(df_plot)} lignes utilisées)")
                    
                    # Option pour télécharger les données utilisées
                    st.download_button(
                        label="Télécharger les données du graphique (CSV)",
                        data=df_plot.to_csv(index=False).encode('utf-8'),
                        file_name=f"{chart_type.lower().replace(' ', '_')}_data.csv",
                        mime="text/csv"
                    )
                    
                except Exception as e:
                    st.error(f"❌ Erreur lors de la création du graphique: {str(e)}")
                    st.info("💡 Vérifiez que les colonnes sélectionnées sont compatibles avec le type de graphique choisi.")
                    # Afficher plus de détails en mode debug
                    with st.expander("Détails de l'erreur (debug)"):
                        st.code(str(e))
            else:
                st.warning(f"Aucune donnée disponible pour la table '{source_endpoint}'")
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # === TABLE ET FILTRES ===
            st.markdown("<div class='section-title'>Données détaillées</div>", unsafe_allow_html=True)
            
            # Afficher le nombre d'éléments en petit
            st.markdown(f"<p style='color: #ffffff; font-size: 0.85rem; margin-bottom: 0.5rem;'>{len(df):,} éléments affichés</p>", unsafe_allow_html=True)
            
            # Sélecteur d'endpoint au-dessus du tableau
            st.markdown("**Sélectionner une table**")
            selected_table = st.selectbox(
                "Table",
                list(ENDPOINTS.keys()),
                index=list(ENDPOINTS.keys()).index(st.session_state.selected_endpoint),
                key="table_selector",
                label_visibility="collapsed"
            )
            
            if selected_table != st.session_state.selected_endpoint:
                st.session_state.selected_endpoint = selected_table
                st.session_state.skip = 0
                st.session_state.all_items = []
                st.session_state.total_count = 0
                st.rerun()
            
            # === FILTRES ET TRI ===
            with st.expander("Filtres et options d'affichage", expanded=False):
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
                    st.info(f"{len(df)} lignes après filtrage")
                
                # Sélection des colonnes à afficher
            
            # Affichage du tableau filtré et trié
            st.dataframe(df, use_container_width=True, height=400)
            
            # Bouton pour télécharger les données filtrées
            col_download1, col_download2 = st.columns([3, 1])
            with col_download2:
                st.download_button(
                    label="Télécharger CSV",
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name=f"{st.session_state.selected_endpoint}_filtered.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            # Bouton pour charger plus d'éléments - avec limite
            if len(st.session_state.all_items) < st.session_state.total_count:
                if st.button("Charger plus d'éléments", use_container_width=True):
                    st.session_state.skip += st.session_state.limit
                    st.rerun()
            
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
