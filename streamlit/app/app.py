import requests
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from chatbot_integration import render_chatbot

# Configuration de la page
st.set_page_config(
    page_title="Safety Analytics Dashboard", 
    layout="wide", 
    initial_sidebar_state="collapsed",
    page_icon="�"
)

# Custom CSS pour un design moderne et professionnel - v2.0
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    /* Style général */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    html, body, .stApp {
        font-size: 16px;
    }
    
    .main {
        padding: 1rem 2rem;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    }
    
    /* Améliorer la lisibilité du texte Streamlit */
    .stMarkdown, .stText, p, span, div {
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
    }
    
    /* Header personnalisé */
    .dashboard-header {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(99, 102, 241, 0.3);
    }
    
    .dashboard-header h1 {
        color: #ffffff;
        font-size: 3rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
    }
    
    .dashboard-header p {
        color: #e0e7ff;
        font-size: 1.25rem;
        margin: 0.5rem 0 0 0;
        font-weight: 400;
    }
    
    /* KPI Cards - VRAIMENT PETITES */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 0.75rem;
        margin-bottom: 1rem;
    }
    
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        padding: 0.6rem 0.8rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid #e2e8f0;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    
    .kpi-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #8b5cf6);
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    
    .kpi-label {
        color: #64748b;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }
    
    .kpi-value {
        color: #0f172a;
        font-size: 1.6rem;
        font-weight: 800;
        margin: 0.2rem 0;
        line-height: 1;
    }
    
    .kpi-change {
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    .kpi-change.positive {
        color: #10b981;
    }
    
    .kpi-change.negative {
        color: #ef4444;
    }
    
    /* Section Cards */
    .section-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    }
    
    .section-title {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 1.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    
    .section-title::before {
        content: '';
        width: 4px;
        height: 2rem;
        background: linear-gradient(180deg, #6366f1, #8b5cf6);
        border-radius: 2px;
    }
    
    /* Event Cards - Dark Mode Compatible */
    .event-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #6366f1;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    }
    
    .event-card:hover {
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);
        transform: translateX(4px);
        background: rgba(30, 41, 59, 0.8);
    }
    
    .event-card-danger {
        border-left-color: #ef4444;
        background: rgba(127, 29, 29, 0.3);
    }
    
    .event-card-danger:hover {
        background: rgba(127, 29, 29, 0.5);
    }
    
    .event-card-warning {
        border-left-color: #f59e0b;
        background: rgba(120, 53, 15, 0.3);
    }
    
    .event-card-warning:hover {
        background: rgba(120, 53, 15, 0.5);
    }
    
    .event-card-success {
        border-left-color: #10b981;
        background: rgba(6, 78, 59, 0.3);
    }
    
    .event-card-success:hover {
        background: rgba(6, 78, 59, 0.5);
    }
    
    .event-card h4 {
        margin: 0 0 0.75rem 0;
        font-size: 1.25rem;
        font-weight: 700;
        color: #f1f5f9 !important;
    }
    
    .event-card p {
        margin: 0.5rem 0;
        color: #cbd5e1 !important;
        font-size: 1rem;
        line-height: 1.5;
    }
    
    .event-card .event-desc {
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(226, 232, 240, 0.2);
        color: #94a3b8 !important;
        font-size: 1rem;
        line-height: 1.6;
    }
    
    .event-badge {
        display: inline-block;
        padding: 0.35rem 0.85rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .badge-danger {
        background: #fef2f2;
        color: #dc2626;
    }
    
    .badge-warning {
        background: #fffbeb;
        color: #d97706;
    }
    
    .badge-success {
        background: #f0fdf4;
        color: #16a34a;
    }
    
    .badge-info {
        background: #eff6ff;
        color: #2563eb;
    }
    
    /* Graphiques */
    .chart-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        margin-bottom: 1.5rem;
    }
    
    .chart-title {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
    }
    
    /* Tabs personnalisés - VRAIMENT GROS */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        background: rgba(255, 255, 255, 0.05);
        padding: 1.25rem;
        border-radius: 20px;
        margin-bottom: 2.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 16px;
        color: #94a3b8;
        font-weight: 800;
        font-size: 1.5rem;
        padding: 1.5rem 3rem;
        transition: all 0.3s ease;
        min-height: 80px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.08);
        color: #c7d2fe;
        transform: scale(1.05);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #ffffff !important;
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.5);
        transform: translateY(-4px) scale(1.05);
    }
    
    /* Boutons personnalisés */
    .stButton > button {
        background: linear-gradient(135deg, #6366f1, #8b5cf6);
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }
    
    /* Scrollbar personnalisée */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(99, 102, 241, 0.5);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(99, 102, 241, 0.7);
    }
    
    /* Animations */
    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-fade-in {
        animation: fadeIn 0.5s ease-out;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# URL de base de l'API
BASE_URL = "http://api:8000"

# Vérification de la connexion API
try:
    res = requests.get(f"{BASE_URL}/", timeout=5)
    if res.status_code != 200:
        st.error("Impossible de se connecter à l'API. Vérifiez que le backend est en cours d'exécution.")
        st.stop()
    infos = res.json()
except:
    st.error("Erreur de connexion à l'API")
    st.stop()

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

# Titre principal avec style moderne
st.markdown("""
<div class="dashboard-header animate-fade-in">
    <h1>Safety Analytics Dashboard</h1>
    <p>Analyse en temps réel des événements de sécurité et mesures correctives</p>
</div>
""", unsafe_allow_html=True)

# Charger toutes les données nécessaires
@st.cache_data(ttl=120)
def load_all_dashboard_data():
    """Charge toutes les données pour le dashboard"""
    data = {}
    
    # Charger events
    events_url = f"{BASE_URL}/events/"
    data['events'] = get_all_data(events_url)
    
    # Charger measures
    measures_url = f"{BASE_URL}/measures/"
    data['measures'] = get_all_data(measures_url)
    
    # Charger risks
    risks_url = f"{BASE_URL}/risks/"
    data['risks'] = get_all_data(risks_url)
    
    # Charger units
    units_url = f"{BASE_URL}/units/"
    data['units'] = get_all_data(units_url)
    
    # Charger persons
    persons_url = f"{BASE_URL}/persons/"
    data['persons'] = get_all_data(persons_url)
    
    return data

with st.spinner("🔄 Chargement du dashboard..."):
    dashboard_data = load_all_dashboard_data()
    
    # Préparer les DataFrames
    df_events = pd.DataFrame(dashboard_data['events']) if dashboard_data['events'] else pd.DataFrame()
    df_measures = pd.DataFrame(dashboard_data['measures']) if dashboard_data['measures'] else pd.DataFrame()
    df_risks = pd.DataFrame(dashboard_data['risks']) if dashboard_data['risks'] else pd.DataFrame()
    df_units = pd.DataFrame(dashboard_data['units']) if dashboard_data['units'] else pd.DataFrame()
    df_persons = pd.DataFrame(dashboard_data['persons']) if dashboard_data['persons'] else pd.DataFrame()
    
    # Ajouter les noms lisibles
    if not df_events.empty and 'organizational_unit_id' in df_events.columns:
        df_events['unit_name'] = df_events['organizational_unit_id'].map(
            lambda x: units_map.get(x, f"Unit {x}") if pd.notna(x) else "Non spécifié"
        )
    
    if not df_measures.empty and 'organizational_unit_id' in df_measures.columns:
        df_measures['unit_name'] = df_measures['organizational_unit_id'].map(
            lambda x: units_map.get(x, f"Unit {x}") if pd.notna(x) else "Non spécifié"
        )

# === TABS POUR ORGANISATION DU CONTENU ===
st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab0, tab3, tab4, tab5 = st.tabs(["Vue d'ensemble", "Événements récents", "Statistiques", "Analyses détaillées", "Créateur de graphiques", "Assistant IA"])

with tab0:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Indicateurs Clés de Performance</div>', unsafe_allow_html=True)
    
    # === KPIs ===
    st.markdown('<div class="kpi-container">', unsafe_allow_html=True)
    kpi_cols = st.columns(3)

    with kpi_cols[0]:
        st.markdown(f"""
        <div class="kpi-card animate-fade-in">
            <div class="kpi-label">Total Événements</div>
            <div class="kpi-value">{len(df_events):,}</div>
            <div class="kpi-change positive">Tous les événements enregistrés</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[1]:
        st.markdown(f"""
        <div class="kpi-card animate-fade-in">
            <div class="kpi-label">Mesures Correctives</div>
            <div class="kpi-value">{len(df_measures):,}</div>
            <div class="kpi-change positive">Actions mises en place</div>
        </div>
        """, unsafe_allow_html=True)

    with kpi_cols[2]:
        total_cost = df_measures['cost'].sum() if not df_measures.empty and 'cost' in df_measures.columns else 0
        st.markdown(f"""
        <div class="kpi-card animate-fade-in">
            <div class="kpi-label">Coût Total</div>
            <div class="kpi-value">{total_cost:,.0f} €</div>
            <div class="kpi-change">Investissement en sécurité</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Statistiques supplémentaires
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Événements par période")
        if not df_events.empty and 'extracted_date' in df_events.columns:
            df_temp = df_events.copy()
            df_temp['extracted_date'] = pd.to_datetime(df_temp['extracted_date'], errors='coerce')
            df_temp = df_temp[df_temp['extracted_date'].notna()]
            if len(df_temp) > 0:
                df_temp['month'] = df_temp['extracted_date'].dt.to_period('M').astype(str)
                monthly = df_temp.groupby('month').size()
                st.metric("Moyenne mensuelle", f"{monthly.mean():.0f}", f"Max: {monthly.max()}")
    
    with col2:
        st.subheader("Unités concernées")
        if not df_events.empty and 'unit_name' in df_events.columns:
            unique_units = df_events['unit_name'].nunique()
            st.metric("Nombre d'unités", f"{unique_units}", f"Sur {len(df_units)} total")

with tab1:
    st.markdown("## Vue d'ensemble des événements")
    
    if not df_events.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Distribution par unité")
            unit_counts = df_events['unit_name'].value_counts().head(10).reset_index()
            unit_counts.columns = ['Unité', 'Nombre']
            
            fig1 = px.bar(unit_counts, x='Unité', y='Nombre',
                         color='Nombre',
                         color_continuous_scale='Viridis',
                         title='')
            fig1.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                font=dict(color='white'),
                xaxis=dict(tickangle=-45),
                showlegend=False
            )
            st.plotly_chart(fig1, use_container_width=True)
        
        with col2:
            st.subheader("Types d'événements")
            if 'type' in df_events.columns:
                type_counts = df_events['type'].value_counts().head(8).reset_index()
                type_counts.columns = ['Type', 'Nombre']
                
                fig2 = px.pie(type_counts, values='Nombre', names='Type',
                             hole=0.4,
                             color_discrete_sequence=px.colors.qualitative.Set3)
                fig2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    showlegend=True,
                    legend=dict(orientation="v", x=1.1, y=0.5)
                )
                st.plotly_chart(fig2, use_container_width=True)
    
    # Mesures et Risques
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("### Mesures correctives")
        
        if not df_measures.empty:
            if 'cost' in df_measures.columns:
                st.subheader("Distribution des coûts")
                df_cost = df_measures[df_measures['cost'].notna()]
                if len(df_cost) > 0:
                    # Filtrer les données pour se concentrer sur les coûts < 100K
                    df_cost_filtered = df_cost[df_cost['cost'] <= 100000]
                    
                    fig3 = px.histogram(df_cost_filtered, x='cost', nbins=30,
                                      color_discrete_sequence=['#8b5cf6'])
                    fig3.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        xaxis_title="Coût (€)",
                        yaxis_title="Nombre",
                        xaxis=dict(range=[0, 100000])
                    )
                    
                    # Ajouter une note si des valeurs sont exclues
                    excluded_count = len(df_cost) - len(df_cost_filtered)
                    if excluded_count > 0:
                        st.caption(f"Note: {excluded_count} mesure(s) > 100K€ non affichée(s) pour une meilleure lisibilité")
                    
                    st.plotly_chart(fig3, use_container_width=True)
    
    with col4:
        st.markdown("### Analyse des risques")
        
        if not df_risks.empty:
            if 'gravity' in df_risks.columns:
                st.subheader("Distribution des niveaux de gravité")
                
                # Compter les occurrences de chaque niveau de gravité
                gravity_counts = df_risks['gravity'].value_counts().sort_index().reset_index()
                gravity_counts.columns = ['Niveau de gravité', 'Nombre de risques']
                
                # Créer un graphique en barres avec dégradé de couleur
                fig4 = px.bar(gravity_counts, 
                             x='Niveau de gravité', 
                             y='Nombre de risques',
                             color='Niveau de gravité',
                             color_continuous_scale='Reds',
                             text='Nombre de risques')
                
                fig4.update_traces(textposition='outside')
                fig4.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    xaxis_title="Niveau de gravité",
                    yaxis_title="Nombre de risques",
                    showlegend=False
                )
                st.plotly_chart(fig4, use_container_width=True)

with tab2:
    st.markdown("## Événements récents")
    
    # Contrôles en haut
    col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 1])
    
    with col_filter1:
        events_per_page = st.selectbox(
            "Événements par page",
            [6, 12, 24, 50],
            index=0,
            key="events_per_page"
        )
    
    with col_filter2:
        if not df_events.empty and 'type' in df_events.columns:
            event_types = ['Tous'] + sorted(df_events['type'].dropna().unique().tolist())
            selected_type = st.selectbox(
                "Filtrer par type",
                event_types,
                key="event_type_filter"
            )
        else:
            selected_type = 'Tous'
    
    with col_filter3:
        st.markdown("<br>", unsafe_allow_html=True)
        if 'event_page' not in st.session_state:
            st.session_state.event_page = 0
    
    if not df_events.empty and 'extracted_date' in df_events.columns:
        df_recent = df_events.copy()
        df_recent['extracted_date'] = pd.to_datetime(df_recent['extracted_date'], errors='coerce')
        df_recent = df_recent.sort_values('extracted_date', ascending=False)
        
        # Filtrer par type si sélectionné
        if selected_type != 'Tous':
            df_recent = df_recent[df_recent['type'] == selected_type]
        
        # Pagination
        total_events = len(df_recent)
        total_pages = (total_events + events_per_page - 1) // events_per_page
        
        # S'assurer que la page actuelle est valide
        if st.session_state.event_page >= total_pages:
            st.session_state.event_page = max(0, total_pages - 1)
        
        start_idx = st.session_state.event_page * events_per_page
        end_idx = min(start_idx + events_per_page, total_events)
        df_page = df_recent.iloc[start_idx:end_idx]
        
        st.markdown(f"<p style='color: #94a3b8; margin-bottom: 1rem;'>Affichage de {start_idx + 1}-{end_idx} sur {total_events} événements</p>", unsafe_allow_html=True)
        
        # Afficher les événements en grille de 3 colonnes
        for i in range(0, len(df_page), 3):
            cols = st.columns(3)
            for j, (idx, event) in enumerate(df_page.iloc[i:i+3].iterrows()):
                with cols[j]:
                    # Déterminer la classe de card
                    classification = str(event.get('classification', '')).lower()
                    if 'danger' in classification or 'critical' in classification or 'grave' in classification:
                        card_class = 'event-card-danger'
                        badge_class = 'badge-danger'
                        badge_text = 'CRITIQUE'
                        icon = '[!]'
                    elif 'warn' in classification or 'moyen' in classification:
                        card_class = 'event-card-warning'
                        badge_class = 'badge-warning'
                        badge_text = 'ATTENTION'
                        icon = '[!]'
                    else:
                        card_class = 'event-card-success'
                        badge_class = 'badge-success'
                        badge_text = 'NORMAL'
                        icon = '[✓]'
                    
                    event_type = event.get('type', 'N/A')
                    event_date = event.get('extracted_date')
                    if pd.notna(event_date):
                        event_date = pd.to_datetime(event_date).strftime('%d/%m/%Y %H:%M')
                        event_date_short = pd.to_datetime(event_date, format='%d/%m/%Y %H:%M').strftime('%d/%m')
                    else:
                        event_date = 'N/A'
                        event_date_short = 'N/A'
                    event_unit = event.get('unit_name', 'Non spécifié')
                    event_desc = str(event.get('description', 'Aucune description'))
                    event_desc_short = event_desc[:80] + '...' if len(event_desc) > 80 else event_desc
                    
                    # Preview courte pour la carte
                    preview_title = f"{icon} {event_type}"
                    
                    # Créer une carte cliquable avec un bouton
                    st.markdown(f"""
                    <div style='background: rgba(30, 41, 59, 0.6); border-radius: 12px; padding: 1rem; margin-bottom: 0.5rem; border: 1px solid rgba(100, 116, 139, 0.3);'>
                        <span class='event-badge {badge_class}' style='display: inline-block; margin-bottom: 0.5rem;'>{badge_text}</span>
                        <h4 style='color: #f1f5f9; margin: 0.5rem 0;'>{preview_title}</h4>
                        <p style='color: #94a3b8; font-size: 0.9rem; margin: 0.3rem 0;'>{event_date_short}</p>
                        <p style='color: #94a3b8; font-size: 0.85rem; margin: 0.3rem 0;'>{event_unit[:30]}</p>
                        <p style='color: #64748b; font-size: 0.85rem; margin-top: 0.5rem;'>{event_desc_short}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Bouton pour ouvrir le dialogue
                    if st.button("Voir les détails", key=f"event_btn_{idx}", use_container_width=True):
                        
                        @st.dialog(f"{icon} {event_type}", width="large")
                        def show_event_details():
                            st.markdown(f"<span class='event-badge {badge_class}' style='display: inline-block; margin-bottom: 1rem;'>{badge_text}</span>", unsafe_allow_html=True)
                            
                            st.markdown("### Informations générales")
                            col1, col2 = st.columns(2)
                            with col1:
                                st.markdown(f"**Date:** {event_date}")
                                st.markdown(f"**Type:** {event_type}")
                            with col2:
                                st.markdown(f"**Unité:** {event_unit}")
                                st.markdown(f"**Classification:** {event.get('classification', 'N/A')}")
                            
                            st.markdown("### Description")
                            st.markdown(f"<p style='color: #cbd5e1; line-height: 1.6;'>{event_desc}</p>", unsafe_allow_html=True)
                        
                        show_event_details()
        
        # Contrôles de pagination
        st.markdown("<br>", unsafe_allow_html=True)
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.button("← Précédent", disabled=(st.session_state.event_page == 0), use_container_width=True):
                st.session_state.event_page -= 1
                st.rerun()
        
        with col_info:
            st.markdown(f"<p style='text-align: center; color: #94a3b8;'>Page {st.session_state.event_page + 1} / {total_pages}</p>", unsafe_allow_html=True)
        
        with col_next:
            if st.button("Suivant →", disabled=(st.session_state.event_page >= total_pages - 1), use_container_width=True):
                st.session_state.event_page += 1
                st.rerun()
    else:
        st.info("Aucun événement récent à afficher")

with tab3:
    st.markdown("## Analyses détaillées par catégorie")
    
    # Sous-tabs pour différentes analyses
    analysis_tab1, analysis_tab2, analysis_tab3 = st.tabs(["Par Unité", "Tendances Temporelles", "Classifications"])
    
    with analysis_tab1:
        if not df_events.empty:
            st.markdown("#### Analyse par unité organisationnelle")
            
            # Top 15 unités avec le plus d'événements
            if 'unit_name' in df_events.columns:
                unit_analysis = df_events['unit_name'].value_counts().head(15).reset_index()
                unit_analysis.columns = ['Unité', 'Nombre d\'événements']
                
                fig = go.Figure(go.Bar(
                    x=unit_analysis['Nombre d\'événements'],
                    y=unit_analysis['Unité'],
                    orientation='h',
                    marker=dict(
                        color=unit_analysis['Nombre d\'événements'],
                        colorscale='Viridis',
                        showscale=True
                    )
                ))
                fig.update_layout(
                    title="Top 15 unités par nombre d'événements",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    height=600,
                    xaxis_title="Nombre d'événements",
                    yaxis_title="Unité"
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Table de statistiques
                st.markdown("**📋 Statistiques détaillées**")
                st.dataframe(unit_analysis, use_container_width=True, height=400)
    
    with analysis_tab2:
        if not df_events.empty and 'extracted_date' in df_events.columns:
            st.markdown("#### Évolution temporelle des événements")
            
            df_temp = df_events.copy()
            df_temp['extracted_date'] = pd.to_datetime(df_temp['extracted_date'], errors='coerce')
            df_temp = df_temp[df_temp['extracted_date'].notna()]
            
            if len(df_temp) > 0:
                # Grouper par mois
                df_temp['month'] = df_temp['extracted_date'].dt.to_period('M').astype(str)
                monthly_counts = df_temp.groupby('month').size().reset_index(name='Nombre')
                
                fig = px.line(monthly_counts, x='month', y='Nombre',
                             markers=True,
                             line_shape='spline')
                fig.update_traces(line=dict(color='#8b5cf6', width=3),
                                marker=dict(size=10, color='#6366f1'))
                fig.update_layout(
                    title="Évolution mensuelle des événements",
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    xaxis_title="Mois",
                    yaxis_title="Nombre d'événements",
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Heatmap par jour de la semaine et semaine
                df_temp['day_of_week'] = df_temp['extracted_date'].dt.day_name()
                df_temp['week'] = df_temp['extracted_date'].dt.isocalendar().week
                
                st.markdown("**Répartition par jour de la semaine**")
                
                # Définir l'ordre des jours de la semaine
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_names_fr = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
                
                # Créer un mapping pour les noms en français
                day_mapping = dict(zip(day_order, day_names_fr))
                
                # Compter et ordonner
                day_counts = df_temp['day_of_week'].value_counts()
                ordered_days = [day for day in day_order if day in day_counts.index]
                ordered_counts = [day_counts[day] for day in ordered_days]
                ordered_labels = [day_mapping[day] for day in ordered_days]
                
                fig2 = px.bar(x=ordered_labels, y=ordered_counts,
                             color=ordered_counts,
                             color_continuous_scale='Purples')
                fig2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='white'),
                    xaxis_title="Jour",
                    yaxis_title="Nombre d'événements",
                    showlegend=False
                )
                st.plotly_chart(fig2, use_container_width=True)
    
    with analysis_tab3:
        if not df_events.empty:
            st.markdown("#### Analyse par classification et type")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'classification' in df_events.columns:
                    st.markdown("**Classifications**")
                    class_counts = df_events['classification'].value_counts().reset_index()
                    class_counts.columns = ['Classification', 'Nombre']
                    
                    fig = px.treemap(class_counts, path=['Classification'], values='Nombre',
                                    color='Nombre',
                                    color_continuous_scale='RdYlGn_r')
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white')
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if 'type' in df_events.columns:
                    st.markdown("**Types d'événements**")
                    type_counts = df_events['type'].value_counts().head(10).reset_index()
                    type_counts.columns = ['Type', 'Nombre']
                    
                    fig = px.bar(type_counts, y='Type', x='Nombre',
                                orientation='h',
                                color='Nombre',
                                color_continuous_scale='Blues')
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='white'),
                        yaxis={'categoryorder':'total ascending'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
    

with tab4:
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
        
        # Extraire le jour de la semaine depuis extracted_date
        if 'extracted_date' in df_custom.columns:
            df_custom['extracted_date_temp'] = pd.to_datetime(df_custom['extracted_date'], errors='coerce')
            df_custom['extracted_weekday'] = df_custom['extracted_date_temp'].dt.day_name()
            df_custom = df_custom.drop('extracted_date_temp', axis=1)
        
        # Extraire le jour de la semaine depuis start_datetime et end_datetime
        if 'start_datetime' in df_custom.columns:
            df_custom['start_datetime_temp'] = pd.to_datetime(df_custom['start_datetime'], errors='coerce')
            df_custom['start_weekday'] = df_custom['start_datetime_temp'].dt.day_name()
            df_custom = df_custom.drop('start_datetime_temp', axis=1)
        
        if 'end_datetime' in df_custom.columns:
            df_custom['end_datetime_temp'] = pd.to_datetime(df_custom['end_datetime'], errors='coerce')
            df_custom['end_weekday'] = df_custom['end_datetime_temp'].dt.day_name()
            df_custom = df_custom.drop('end_datetime_temp', axis=1)
        
        # Nettoyer extracted_shift
        if 'extracted_shift' in df_custom.columns:
            df_custom['extracted_shift'] = df_custom['extracted_shift'].str.strip().str.lower()
            df_custom.loc[~df_custom['extracted_shift'].isin(['day', 'night']), 'extracted_shift'] = None
        
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
            ["Bar Chart", "Line Chart", "Scatter Plot", "Pie Chart", "Histogram"],
            help="Sélectionnez le type de visualisation"
        )
        
        # Messages d'aide selon le type de graphique
        chart_requirements = {
            "Bar Chart": "📊 Recommandé: X = catégorie, Y = valeur numérique",
            "Line Chart": "📈 Recommandé: X = temps/ordre, Y = valeur numérique",
            "Scatter Plot": "🔵 Nécessite: X et Y numériques pour analyser les corrélations",
            "Pie Chart": "🥧 Nécessite: Catégories (max 15 pour la lisibilité)",
            "Histogram": "📊 Nécessite: Une colonne numérique pour la distribution"
        }
        st.info(chart_requirements[chart_type])
        
        # Axe X avec filtrage intelligent selon le type de graphique
        if chart_type not in ["Pie Chart", "Histogram"]:
            if chart_type == "Scatter Plot":
                # Pour scatter, on recommande du numérique
                x_options = numeric_columns if numeric_columns else available_columns
                x_axis = st.selectbox(
                    "Axe X (numérique recommandé)",
                    x_options,
                    help="Choisissez une colonne numérique pour l'axe X"
                )
            elif chart_type in ["Bar Chart"]:
                # Pour bar, on recommande du catégoriel
                x_options = good_categorical_columns if good_categorical_columns else available_columns
                x_axis = st.selectbox(
                    "Axe X (catégorie recommandée)",
                    x_options,
                    help="Choisissez une colonne catégorielle pour l'axe X"
                )
            else:
                # Line accepte les deux
                x_axis = st.selectbox(
                    "Axe X",
                    available_columns,
                    help="Choisissez la colonne pour l'axe X"
                )
        
        # Axe Y avec filtrage intelligent
        if chart_type not in ["Pie Chart"]:
            if chart_type == "Histogram":
                if not numeric_columns:
                    st.warning("⚠️ Aucune colonne numérique disponible pour un histogramme")
                    validation_errors.append("Histogramme nécessite une colonne numérique")
                y_axis = st.selectbox(
                    "Valeur à analyser (numérique)",
                    numeric_columns if numeric_columns else available_columns,
                    help="Choisissez la colonne numérique pour l'histogramme"
                )
            elif chart_type in ["Scatter Plot", "Line Chart", "Bar Chart"]:
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
        
        # Options pour Pie Chart
        if chart_type in ["Pie Chart"]:
            if not good_categorical_columns:
                st.error("❌ Aucune colonne catégorielle appropriée trouvée pour ce type de graphique")
                validation_errors.append("Pie nécessite des colonnes catégorielles avec moins de 50 valeurs")
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
    
    # Options supplémentaires
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        chart_title = st.text_input("Titre du graphique", value=f"{chart_type} personnalisé")
    with col_opt2:
        if chart_type in ["Bar Chart", "Line Chart", "Pie Chart", "Histogram"]:
            aggregation = st.selectbox(
                "Agrégation",
                ["Aucune", "Somme", "Moyenne", "Nombre de", "Min", "Max"],
                help="Comment agréger les données"
            )
            if chart_type in ["Pie Chart", "Histogram"]:
                if aggregation in ["Somme", "Moyenne", "Min", "Max"]:
                    st.info(f"💡 Pour {chart_type}, l'agrégation '{aggregation}' s'applique aux valeurs")
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
    
    elif chart_type in ["Pie Chart"]:
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
    
    elif chart_type in ["Bar Chart", "Line Chart"]:
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
                    # Déterminer les colonnes pour le groupby
                    group_cols = [x_axis]
                    if color_column:
                        group_cols.append(color_column)
                    
                    if aggregation == "Somme":
                        df_plot = df_plot.groupby(group_cols)[y_axis].sum().reset_index()
                    elif aggregation == "Moyenne":
                        df_plot = df_plot.groupby(group_cols)[y_axis].mean().reset_index()
                    elif aggregation == "Nombre de":
                        df_plot = df_plot.groupby(group_cols).size().reset_index(name=y_axis)
                    elif aggregation == "Min":
                        df_plot = df_plot.groupby(group_cols)[y_axis].min().reset_index()
                    elif aggregation == "Max":
                        df_plot = df_plot.groupby(group_cols)[y_axis].max().reset_index()
                
                # Déterminer le label de l'axe Y
                y_label = f"{aggregation} {y_axis}" if aggregation != "Aucune" else y_axis
                
                fig = px.bar(df_plot, x=x_axis, y=y_axis, color=color_column, 
                            title=chart_title, height=chart_height,
                            labels={y_axis: y_label})
                
                # Personnaliser le hover template
                if aggregation != "Aucune":
                    hover_template = f'<b>{x_axis}</b>: %{{x}}<br>{y_label}: %{{y}}'
                    if color_column:
                        hover_template += f'<br><b>{color_column}</b>: %{{fullData.name}}'
                    hover_template += '<extra></extra>'
                    fig.update_traces(hovertemplate=hover_template)
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "Line Chart":
                df_plot = df_plot.dropna(subset=[x_axis, y_axis])
                
                if len(df_plot) == 0:
                    st.error("❌ Aucune donnée valide après nettoyage")
                    st.stop()
                
                if aggregation != "Aucune" and x_axis and y_axis:
                    # Déterminer les colonnes pour le groupby
                    group_cols = [x_axis]
                    if color_column:
                        group_cols.append(color_column)
                    
                    if aggregation == "Somme":
                        df_plot = df_plot.groupby(group_cols)[y_axis].sum().reset_index()
                    elif aggregation == "Moyenne":
                        df_plot = df_plot.groupby(group_cols)[y_axis].mean().reset_index()
                    elif aggregation == "Nombre de":
                        df_plot = df_plot.groupby(group_cols).size().reset_index(name=y_axis)
                
                # Déterminer le label de l'axe Y
                y_label = f"{aggregation} {y_axis}" if aggregation != "Aucune" else y_axis
                
                fig = px.line(df_plot, x=x_axis, y=y_axis, color=color_column,
                                title=chart_title, height=chart_height,
                                labels={y_axis: y_label})
                
                # Personnaliser le hover template
                if aggregation != "Aucune":
                    hover_template = f'<b>{x_axis}</b>: %{{x}}<br>{y_label}: %{{y}}'
                    if color_column:
                        hover_template += f'<br><b>{color_column}</b>: %{{fullData.name}}'
                    hover_template += '<extra></extra>'
                    fig.update_traces(hovertemplate=hover_template)
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
                # Appliquer l'agrégation si nécessaire
                if aggregation != "Aucune" and names_column:
                    if values_column:
                        # Si une colonne de valeurs est spécifiée
                        df_plot = df_plot.dropna(subset=[names_column, values_column])
                        
                        if aggregation == "Somme":
                            df_plot = df_plot.groupby(names_column)[values_column].sum().reset_index()
                        elif aggregation == "Moyenne":
                            df_plot = df_plot.groupby(names_column)[values_column].mean().reset_index()
                        elif aggregation == "Nombre de":
                            df_plot = df_plot.groupby(names_column).size().reset_index(name=values_column)
                        elif aggregation == "Min":
                            df_plot = df_plot.groupby(names_column)[values_column].min().reset_index()
                        elif aggregation == "Max":
                            df_plot = df_plot.groupby(names_column)[values_column].max().reset_index()
                        
                        # Limiter à 15 catégories max
                        if len(df_plot) > 15:
                            st.info("ℹ️ Affichage des 15 catégories principales")
                            df_plot = df_plot.nlargest(15, values_column)
                        
                        fig = px.pie(df_plot, names=names_column, values=values_column,
                                    title=chart_title, height=chart_height)
                    else:
                        # Sans colonne de valeurs, toujours compter
                        df_counts = df_plot[names_column].value_counts().reset_index()
                        df_counts.columns = [names_column, 'count']
                        if len(df_counts) > 15:
                            st.info("ℹ️ Affichage des 15 catégories principales")
                            df_counts = df_counts.head(15)
                        fig = px.pie(df_counts, names=names_column, values='count',
                                    title=chart_title, height=chart_height)
                else:
                    # Logique originale sans agrégation
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
                
                # Si agrégation et couleur sont spécifiées
                if aggregation != "Aucune" and color_column:
                    group_cols = [color_column]
                    
                    if aggregation == "Somme":
                        df_agg = df_plot.groupby(group_cols)[y_axis].sum().reset_index()
                    elif aggregation == "Moyenne":
                        df_agg = df_plot.groupby(group_cols)[y_axis].mean().reset_index()
                    elif aggregation == "Nombre de":
                        df_agg = df_plot.groupby(group_cols).size().reset_index(name=y_axis)
                    elif aggregation == "Min":
                        df_agg = df_plot.groupby(group_cols)[y_axis].min().reset_index()
                    elif aggregation == "Max":
                        df_agg = df_plot.groupby(group_cols)[y_axis].max().reset_index()
                    else:
                        df_agg = df_plot
                    
                    # Créer un bar chart au lieu d'un histogramme pour les données agrégées
                    y_label = f"{aggregation} {y_axis}"
                    fig = px.bar(df_agg, x=color_column, y=y_axis, color=color_column,
                                title=chart_title, height=chart_height,
                                labels={y_axis: y_label})
                    st.info("ℹ️ Avec agrégation, affichage d'un graphique à barres plutôt qu'un histogramme")
                else:
                    # Histogramme normal sans agrégation
                    fig = px.histogram(df_plot, x=y_axis, color=color_column,
                                        title=chart_title, height=chart_height, nbins=30)
                
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
            

    # st.markdown("## Créateur de graphiques personnalisés")
    
    # st.info("Créez vos propres visualisations à partir des données disponibles")
    
    # # Sélection de la source de données
    # col_src1, col_src2 = st.columns([1, 2])
    # with col_src1:
    #     source_table = st.selectbox(
    #         "Source de données",
    #         ["events", "measures", "risks", "units", "persons"],
    #         help="Sélectionnez la table source"
    #     )
    
    # with col_src2:
    #     # Charger les données selon la source sélectionnée
    #     if source_table == "events":
    #         df_source = df_events.copy()
    #     elif source_table == "measures":
    #         df_source = df_measures.copy()
    #     elif source_table == "risks":
    #         df_source = df_risks.copy()
    #     elif source_table == "units":
    #         df_source = df_units.copy()
    #     elif source_table == "persons":
    #         df_source = df_persons.copy()
        
    #     st.metric("Nombre de lignes", f"{len(df_source):,}")
    
    # if not df_source.empty:
    #     # Configuration du graphique
    #     col_chart1, col_chart2 = st.columns(2)
        
    #     with col_chart1:
    #         chart_type = st.selectbox(
    #             "Type de graphique",
    #             ["Bar", "Pie", "Line", "Scatter", "Histogram", "Box"],
    #             help="Choisissez le type de visualisation"
    #         )
        
    #     with col_chart2:
    #         numeric_cols = list(df_source.select_dtypes(include=[np.number]).columns)
    #         categorical_cols = list(df_source.select_dtypes(include=['object', 'category']).columns)
            
    #         if chart_type in ["Bar", "Pie"]:
    #             if categorical_cols:
    #                 group_col = st.selectbox("Grouper par", categorical_cols)
    #             else:
    #                 st.warning("Aucune colonne catégorielle disponible")
    #                 group_col = None
    #         elif chart_type in ["Line", "Scatter", "Histogram", "Box"]:
    #             if numeric_cols:
    #                 value_col = st.selectbox("Valeur à analyser", numeric_cols)
    #             else:
    #                 st.warning("Aucune colonne numérique disponible")
    #                 value_col = None
        
    #     # Génération du graphique
    #     if st.button("Générer le graphique", type="primary", use_container_width=True):
    #         try:
    #             if chart_type == "Bar" and group_col:
    #                 counts = df_source[group_col].value_counts().head(15)
    #                 fig = px.bar(x=counts.index, y=counts.values,
    #                            labels={'x': group_col, 'y': 'Count'},
    #                            color=counts.values,
    #                            color_continuous_scale='Viridis')
    #                 fig.update_layout(
    #                     title=f"Distribution - {group_col}",
    #                     plot_bgcolor='rgba(0,0,0,0)',
    #                     paper_bgcolor='rgba(0,0,0,0)',
    #                     font=dict(color='white')
    #                 )
    #                 st.plotly_chart(fig, use_container_width=True)
                
    #             elif chart_type == "Pie" and group_col:
    #                 counts = df_source[group_col].value_counts().head(10)
    #                 fig = px.pie(values=counts.values, names=counts.index,
    #                            title=f"Répartition - {group_col}",
    #                            hole=0.4)
    #                 fig.update_layout(
    #                     plot_bgcolor='rgba(0,0,0,0)',
    #                     paper_bgcolor='rgba(0,0,0,0)',
    #                     font=dict(color='white')
    #                 )
    #                 st.plotly_chart(fig, use_container_width=True)
                
    #             elif chart_type == "Histogram" and 'value_col' in locals() and value_col:
    #                 fig = px.histogram(df_source, x=value_col, nbins=30,
    #                                  color_discrete_sequence=['#8b5cf6'])
    #                 fig.update_layout(
    #                     title=f"Distribution - {value_col}",
    #                     plot_bgcolor='rgba(0,0,0,0)',
    #                     paper_bgcolor='rgba(0,0,0,0)',
    #                     font=dict(color='white')
    #                 )
    #                 st.plotly_chart(fig, use_container_width=True)
                
    #             elif chart_type == "Box" and 'value_col' in locals() and value_col:
    #                 fig = px.box(df_source, y=value_col,
    #                            color_discrete_sequence=['#6366f1'])
    #                 fig.update_layout(
    #                     title=f"Box Plot - {value_col}",
    #                     plot_bgcolor='rgba(0,0,0,0)',
    #                     paper_bgcolor='rgba(0,0,0,0)',
    #                     font=dict(color='white')
    #                 )
    #                 st.plotly_chart(fig, use_container_width=True)
                
    #             st.success("Graphique généré avec succès!")
                
    #         except Exception as e:
    #             st.error(f"Erreur: {str(e)}")
    # else:
    #     st.warning("Aucune donnée disponible pour cette table")

with tab5:
    render_chatbot()

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #94a3b8; padding: 2rem 0; font-size: 0.875rem;'>
    <p>Safety Analytics Dashboard | Powered by Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)
