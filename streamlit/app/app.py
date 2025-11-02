import requests
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from chatbot_integration import render_chatbot
import google.generativeai as genai
from PIL import Image
import io
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Fonction pour analyser une image avec Gemini
def analyze_event_image_with_gemini(image_file):
    """Analyse une image d'événement avec Gemini et génère une description."""
    try:
        # Configurer l'API Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None, "⚠️ Clé API Gemini non trouvée. Veuillez configurer GEMINI_API_KEY."
        
        genai.configure(api_key=api_key)
        
        # Charger l'image
        image = Image.open(image_file)
        
        # Initialiser le modèle
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Créer le prompt pour l'analyse
        prompt = """Analyse cette image d'événement de sécurité et génère une description détaillée et professionnelle en français.

La description doit suivre ce format narratif détaillé (voir exemples) :

EXEMPLE 1 (déversement chimique):
"Le 2 avril 2024, vers 21h45 durant le quart de soir, Natasha Ivanov (EMP-00136), spécialiste en inventaire chimique, effectuait une vérification d'inventaire de routine dans la zone de gestion des déchets dangereux (UNIT-011). Alors qu'elle déplaçait un baril de 55 gallons d'acétone (solvant de nettoyage) à l'aide d'un diable pour le repositionner dans le cadre de la rotation des stocks, le bouchon du baril s'est partiellement dégagé en raison des vibrations durant le transport. Environ 12-15 litres d'acétone se sont déversés sur le plancher de béton et ont commencé à former une flaque près de l'armoire de stockage chimique. Les vapeurs volatiles se sont rapidement dispersées dans la zone extérieure. Natasha a immédiatement activé le système de ventilation d'urgence et s'est évacuée à 8 mètres contre le vent du déversement. Elle a notifié Luc-André Beaudoin (EMP-00139), superviseur d'entrepôt, qui a initié les procédures de confinement. Le déversement a été confiné avec des tampons absorbants et éliminé selon les protocoles CNESST. Aucun employé n'a éprouvé de symptômes d'exposition chimique aiguë. L'incident a été attribué à un mauvais scellage du bouchon lors du cycle d'inventaire précédent et à un amortissement inadéquat des vibrations sur le diable."

EXEMPLE 2 (exposition à des vapeurs):
"Le 14 mars 2024, vers 14h15 durant le quart de jour, le technicien de moulage Stéphane Moreau (EMP-00021) retirait un moule d'injection complété de la ligne de moulage C dans la salle blanche des composants médicaux (UNIT-003). Il utilisait un agent de démoulage en aérosol standard. Alors qu'il vaporisait la surface du moule à courte distance sans ajustement adéquat de la ventilation, les vapeurs de solvant se sont accumulées dans l'espace de travail fermé. Après 8 minutes de vaporisation continue, Stéphane a ressenti des étourdissements aigus, des maux de tête et de légères nausées. L'opérateur de machine Emmanuel Kouassi (EMP-00058) a remarqué que Stéphane titubait et a immédiatement appelé à l'aide. Le superviseur de production Maxime Boisvert (EMP-00101) est arrivé en 2 minutes et a déplacé Stéphane vers la salle de pause à l'air frais. Les symptômes se sont résorbés en 15 minutes. L'infirmière en santé au travail Hana Al-Rashid (EMP-00052) a effectué une évaluation et déterminé que l'incident était causé par une ventilation d'extraction locale inadéquate et une technique de travail inappropriée."

INSTRUCTIONS IMPORTANTES:
- Décris UNIQUEMENT ce qui est visible dans l'image
- Si la date, l'heure, les noms de personnes, ou les identifiants ne sont pas visibles : N'INVENTE PAS ces informations
- Utilise des formulations génériques comme : "Durant les opérations...", "Un employé...", "Un travailleur...", "Dans la zone de..."
- Concentre-toi sur : le type d'événement, l'équipement visible, les conditions observables, les risques identifiables
- Reste factuel et professionnel
- Rédige 3-5 phrases décrivant la situation visible

Génère maintenant une description détaillée basée UNIQUEMENT sur ce qui est visible dans l'image."""

        # Générer la description
        response = model.generate_content([prompt, image])
        
        if response and response.text:
            return response.text.strip(), None
        else:
            return None, "❌ Aucune réponse générée par Gemini."
            
    except Exception as e:
        return None, f"❌ Erreur lors de l'analyse de l'image : {str(e)}"

# Configuration de la page
st.set_page_config(
    page_title="Safety Analytics Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded",
    page_icon="📊"
)

# Custom CSS pour un design moderne et professionnel - v2.0
st.markdown("""
<style>
    /* Force la sidebar à rester ouverte */
    section[data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
    }
    
    /* Masquer le bouton de fermeture de la sidebar - toutes les variantes */
    button[kind="header"],
    section[data-testid="stSidebar"] button[kind="headerNoPadding"],
    section[data-testid="stSidebar"] > div > button,
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Masquer les boutons radio (bulles) dans la sidebar */
    section[data-testid="stSidebar"] input[type="radio"] {
        display: none !important;
    }
    
    /* Masquer complètement les cercles/ronds des radio buttons */
    section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }
    
    section[data-testid="stSidebar"] [role="radio"] {
        display: none !important;
    }
    
    /* Style des labels de navigation pour qu'ils ressemblent à des boutons */
    section[data-testid="stSidebar"] label[data-baseweb="radio"] {
        cursor: pointer !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
        background: transparent !important;
        margin: 0.25rem 0 !important;
    }
    
    section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
        background: rgba(99, 102, 241, 0.1) !important;
    }
    
    /* Style pour l'élément sélectionné */
    section[data-testid="stSidebar"] label[data-baseweb="radio"] div[data-checked="true"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        color: white !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
    }
    
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

# === SIDEBAR POUR NAVIGATION ===
st.sidebar.title("📊 Navigation")
st.sidebar.markdown("---")

# Menu de navigation dans la sidebar
page = st.sidebar.radio(
    "Sélectionnez une page :",
    ["🤖 Assistant IA", "🏠 Vue d'ensemble", "📅 Événements récents", "📊 Statistiques", "🔍 Analyses détaillées", "🎨 Créateur de graphiques", "✏️ Gestion des données"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style='font-size: 0.8rem; color: #94a3b8;'>
    <p><b>Safety Analytics Dashboard</b></p>
    <p>Powered by Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)

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

# === CONTENU EN FONCTION DE LA PAGE SÉLECTIONNÉE ===

if page == "🤖 Assistant IA":
    render_chatbot()

elif page == "📊 Statistiques":
    st.markdown("## 📊 Indicateurs Clés de Performance")
    
    # === KPIs ===
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
        if not df_events.empty and 'start_datetime' in df_events.columns:
            df_temp = df_events.copy()
            df_temp['start_datetime'] = pd.to_datetime(df_temp['start_datetime'], errors='coerce')
            df_temp = df_temp[df_temp['start_datetime'].notna()]
            if len(df_temp) > 0:
                df_temp['month'] = df_temp['start_datetime'].dt.to_period('M').astype(str)
                monthly = df_temp.groupby('month').size()
                st.metric("Moyenne mensuelle", f"{monthly.mean():.0f}", f"Max: {monthly.max()}")
    
    with col2:
        st.subheader("Unités concernées")
        if not df_events.empty and 'unit_name' in df_events.columns:
            unique_units = df_events['unit_name'].nunique()
            st.metric("Nombre d'unités", f"{unique_units}", f"Sur {len(df_units)} total")

elif page == "🏠 Vue d'ensemble":
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

elif page == "📅 Événements récents":
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
    
    if not df_events.empty and 'start_datetime' in df_events.columns:
        df_recent = df_events.copy()
        df_recent['start_datetime'] = pd.to_datetime(df_recent['start_datetime'], errors='coerce')
        df_recent = df_recent.sort_values('start_datetime', ascending=False)
        
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
                    event_date = event.get('start_datetime')
                    if pd.notna(event_date):
                        event_date_parsed = pd.to_datetime(event_date)
                        event_date = event_date_parsed.strftime('%d/%m/%Y %H:%M')
                        event_date_short = event_date_parsed.strftime('%d/%m')
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

elif page == "🔍 Analyses détaillées":
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
        if not df_events.empty and 'start_datetime' in df_events.columns:
            st.markdown("#### Évolution temporelle des événements")
            
            df_temp = df_events.copy()
            df_temp['start_datetime'] = pd.to_datetime(df_temp['start_datetime'], errors='coerce')
            df_temp = df_temp[df_temp['start_datetime'].notna()]
            
            if len(df_temp) > 0:
                # Grouper par mois
                df_temp['month'] = df_temp['start_datetime'].dt.to_period('M').astype(str)
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
                df_temp['day_of_week'] = df_temp['start_datetime'].dt.day_name()
                df_temp['week'] = df_temp['start_datetime'].dt.isocalendar().week
                
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
    

elif page == "🎨 Créateur de graphiques":
    # === CRÉATEUR DE GRAPHIQUES PERSONNALISÉS ===
    st.markdown("---")
    st.subheader("Créateur de graphiques personnalisés")
    
    # Initialiser date_columns
    date_columns = []
    
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
        
        # Identifier et convertir les colonnes de dates
        date_columns = []
        for col in df_custom.columns:
            if col in ['start_datetime', 'end_datetime', 'creation_date', 'update_date', 'date', 'datetime', 'implementation_date']:
                # Convertir en datetime et garder le type datetime
                df_custom[col] = pd.to_datetime(df_custom[col], errors='coerce')
                date_columns.append(col)
        
        # Extraire le jour de la semaine depuis start_datetime et end_datetime
        if 'start_datetime' in df_custom.columns:
            df_custom['start_weekday'] = df_custom['start_datetime'].dt.day_name()
        
        if 'end_datetime' in df_custom.columns:
            df_custom['end_weekday'] = df_custom['end_datetime'].dt.day_name()
        
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
            
            # Détecter si x_axis est une colonne de date et la trier
            is_x_date = False
            if x_axis and x_axis in date_columns:
                is_x_date = True
                df_plot = df_plot.sort_values(by=x_axis)
                st.info(f"📅 Colonne de date détectée: tri chronologique appliqué sur {x_axis}")
            
            # Créer le graphique selon le type
            if chart_type == "Bar Chart":
                # Nettoyer les données
                df_plot = df_plot.dropna(subset=[x_axis, y_axis])
                
                if len(df_plot) == 0:
                    st.error("❌ Aucune donnée valide après nettoyage")
                    st.stop()
                
                # Limiter le nombre de catégories pour éviter les graphiques surchargés
                # Mais seulement si ce n'est pas une date
                if not is_x_date and df_plot[x_axis].nunique() > 50:
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
                    
                    # Re-trier par date après l'agrégation si nécessaire
                    if is_x_date:
                        df_plot = df_plot.sort_values(by=x_axis)
                
                # Déterminer le label de l'axe Y
                y_label = f"{aggregation} {y_axis}" if aggregation != "Aucune" else y_axis
                
                fig = px.bar(df_plot, x=x_axis, y=y_axis, color=color_column, 
                            title=chart_title, height=chart_height,
                            labels={y_axis: y_label})
                
                # Si c'est une date, formater l'axe X
                if is_x_date:
                    fig.update_xaxes(tickformat="%Y-%m-%d", tickangle=-45)
                
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
                    
                    # Re-trier par date après l'agrégation si nécessaire
                    if is_x_date:
                        df_plot = df_plot.sort_values(by=x_axis)
                
                # Déterminer le label de l'axe Y
                y_label = f"{aggregation} {y_axis}" if aggregation != "Aucune" else y_axis
                
                fig = px.line(df_plot, x=x_axis, y=y_axis, color=color_column,
                                title=chart_title, height=chart_height,
                                labels={y_axis: y_label})
                
                # Si c'est une date, formater l'axe X
                if is_x_date:
                    fig.update_xaxes(tickformat="%Y-%m-%d", tickangle=-45)
                
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

elif page == "✏️ Gestion des données":
    st.markdown("## ✏️ Gestion des données (CRUD)")
    st.info("Créer, mettre à jour ou supprimer des enregistrements dans la base de données")
    
    # Sélection de l'action
    col_action, col_table = st.columns(2)
    
    with col_action:
        action = st.selectbox(
            "Action à effectuer",
            ["CREATE - Créer", "UPDATE - Modifier", "DELETE - Supprimer"],
            help="Choisissez l'opération CRUD"
        )
        action_type = action.split(" - ")[0]
    
    with col_table:
        table_options = {
            "events": "Événements",
            "persons": "Personnes",
            "units": "Unités organisationnelles",
            "measures": "Mesures correctives",
            "risks": "Risques"
        }
        selected_table = st.selectbox(
            "Table",
            list(table_options.keys()),
            format_func=lambda x: table_options[x],
            help="Choisissez la table à modifier"
        )
    
    st.markdown("---")
    
    # Fonction pour détecter le type de champ dynamiquement
    def detect_field_type(field_name: str, sample_value) -> dict:
        """Détecte automatiquement le type d'un champ basé sur son nom et sa valeur."""
        field_name_lower = field_name.lower()
        
        # Primary key ID fields - readonly (event_id, person_id, etc.)
        if field_name_lower in ['event_id', 'person_id', 'unit_id', 'measure_id', 'risk_id']:
            return {"type": "number", "label": field_name.replace('_', ' ').title(), "readonly": True, "required": False}
        
        # Foreign key ID fields - required (declared_by_id, organizational_unit_id, owner_id)
        if field_name_lower.endswith('_id') or field_name_lower == 'id':
            return {"type": "number", "label": field_name.replace('_', ' ').title(), "readonly": False, "required": True}
        
        # Datetime fields
        if 'datetime' in field_name_lower or 'date' in field_name_lower:
            return {"type": "datetime", "label": field_name.replace('_', ' ').title(), "required": True}
        
        # Description fields - textarea
        if 'description' in field_name_lower:
            return {"type": "textarea", "label": field_name.replace('_', ' ').title(), "required": True}
        
        # Cost/Price fields - number with optional
        if 'cost' in field_name_lower or 'price' in field_name_lower or 'amount' in field_name_lower:
            return {"type": "number", "label": field_name.replace('_', ' ').title(), "required": False}
        
        # Detect based on sample value type
        if sample_value is not None:
            if isinstance(sample_value, (int, float)):
                return {"type": "number", "label": field_name.replace('_', ' ').title(), "required": True}
            elif isinstance(sample_value, str) and len(sample_value) > 100:
                return {"type": "textarea", "label": field_name.replace('_', ' ').title(), "required": True}
        
        # Default to text
        return {"type": "text", "label": field_name.replace('_', ' ').title(), "required": True}
    
    # Récupérer un exemple d'enregistrement pour détecter les champs dynamiquement
    fields = {}
    id_field = None
    
    try:
        with st.spinner("🔍 Détection des champs..."):
            response = requests.get(f"{BASE_URL}/{selected_table}/", params={"limit": 1}, timeout=5)
            if response.status_code == 200:
                records = response.json()
                if records and len(records) > 0:
                    sample_record = records[0]
                    
                    # Créer les champs dynamiquement
                    for field_name, field_value in sample_record.items():
                        fields[field_name] = detect_field_type(field_name, field_value)
                    
                    # Identifier le champ ID (premier champ avec _id ou id)
                    for field_name in fields.keys():
                        if field_name.lower().endswith('_id') or field_name.lower() == 'id':
                            id_field = field_name
                            break
                    
                    if not id_field:
                        # Si aucun ID trouvé, prendre le premier champ
                        id_field = list(fields.keys())[0]
                    
                    st.success(f"✅ {len(fields)} champs détectés automatiquement")
                else:
                    st.warning("⚠️ Aucun enregistrement dans la table. Impossible de détecter les champs automatiquement.")
                    st.info("💡 Ajoutez au moins un enregistrement manuellement via l'API pour activer la détection automatique.")
                    st.stop()
            else:
                st.error(f"❌ Erreur lors de la récupération des données: {response.status_code}")
                st.stop()
    except Exception as e:
        st.error(f"❌ Erreur lors de la détection des champs: {str(e)}")
        st.stop()
    
    # DELETE
    if action_type == "DELETE":
        st.markdown(f"### 🗑️ Supprimer un enregistrement de {table_options[selected_table]}")
        
        # Récupérer tous les enregistrements
        try:
            response = requests.get(f"{BASE_URL}/{selected_table}/", params={"limit": 1000}, timeout=5)
            if response.status_code == 200:
                records = response.json()
                if records:
                    # Créer un mapping ID -> description lisible
                    record_options = {}
                    for record in records:
                        record_id = record[id_field]
                        # Créer une description selon la table
                        if selected_table == "events":
                            desc = f"#{record_id} - {record.get('type', 'N/A')} ({record.get('classification', 'N/A')})"
                        elif selected_table == "persons":
                            desc = f"#{record_id} - {record.get('name', '')} {record.get('family_name', '')}"
                        elif selected_table == "units":
                            desc = f"#{record_id} - {record.get('name', 'N/A')}"
                        elif selected_table == "measures":
                            desc = f"#{record_id} - {record.get('name', 'N/A')}"
                        elif selected_table == "risks":
                            desc = f"#{record_id} - {record.get('name', 'N/A')}"
                        record_options[record_id] = desc
                    
                    selected_id = st.selectbox(
                        "Sélectionnez l'enregistrement à supprimer",
                        list(record_options.keys()),
                        format_func=lambda x: record_options[x]
                    )
                    
                    # Afficher les détails de l'enregistrement
                    selected_record = next(r for r in records if r[id_field] == selected_id)
                    with st.expander("📋 Détails de l'enregistrement"):
                        st.json(selected_record)
                    
                    st.warning("⚠️ Cette action est irréversible !")
                    
                    if st.button("🗑️ Confirmer la suppression", type="primary", use_container_width=True):
                        try:
                            delete_response = requests.delete(f"{BASE_URL}/{selected_table}/{selected_id}", timeout=5)
                            if delete_response.status_code in [200, 204]:
                                st.success(f"✅ Enregistrement #{selected_id} supprimé avec succès !")
                                st.balloons()
                                # Invalider le cache
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(f"❌ Erreur lors de la suppression: HTTP {delete_response.status_code}")
                                if delete_response.text:
                                    st.error(f"Détails: {delete_response.text}")
                        except Exception as e:
                            st.error(f"❌ Erreur: {str(e)}")
                else:
                    st.info("Aucun enregistrement trouvé dans cette table")
            else:
                st.error(f"❌ Erreur lors de la récupération des données: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")
    
    # UPDATE
    elif action_type == "UPDATE":
        st.markdown(f"### ✏️ Modifier un enregistrement de {table_options[selected_table]}")
        
        # Charger les options pour les sélecteurs
        @st.cache_data(ttl=60)
        def get_selector_options(table_name):
            """Récupère les données d'une table pour les sélecteurs"""
            try:
                resp = requests.get(f"{BASE_URL}/{table_name}/", params={"limit": 1000}, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
            except:
                pass
            return []
        
        # Récupérer tous les enregistrements
        try:
            response = requests.get(f"{BASE_URL}/{selected_table}/", params={"limit": 1000}, timeout=5)
            if response.status_code == 200:
                records = response.json()
                if records:
                    # Créer un mapping ID -> description lisible
                    record_options = {}
                    for record in records:
                        record_id = record[id_field]
                        if selected_table == "events":
                            desc = f"#{record_id} - {record.get('type', 'N/A')}"
                        elif selected_table == "persons":
                            desc = f"#{record_id} - {record.get('name', '')} {record.get('family_name', '')}"
                        elif selected_table == "units":
                            desc = f"#{record_id} - {record.get('name', 'N/A')}"
                        elif selected_table == "measures":
                            desc = f"#{record_id} - {record.get('name', 'N/A')}"
                        elif selected_table == "risks":
                            desc = f"#{record_id} - {record.get('name', 'N/A')}"
                        record_options[record_id] = desc
                    
                    selected_id = st.selectbox(
                        "Sélectionnez l'enregistrement à modifier",
                        list(record_options.keys()),
                        format_func=lambda x: record_options[x]
                    )
                    
                    # Récupérer l'enregistrement complet
                    selected_record = next(r for r in records if r[id_field] == selected_id)
                    
                    # Charger les catégories existantes pour type et classification
                    event_types = []
                    event_classifications = []
                    if selected_table == "events":
                        all_events = get_selector_options("events")
                        if all_events:
                            event_types = sorted(list(set([e.get('type') for e in all_events if e.get('type')])))
                            event_classifications = sorted(list(set([e.get('classification') for e in all_events if e.get('classification')])))
                    
                    st.markdown("#### Modifier les champs")
                    
                    # Formulaire avec les valeurs pré-remplies
                    form_data = {}
                    
                    for field_name, field_info in fields.items():
                        if field_info.get("readonly", False):
                            st.text_input(field_info["label"], value=str(selected_record.get(field_name, "")), disabled=True)
                            continue
                        
                        current_value = selected_record.get(field_name)
                        
                        # Sélecteurs pour les clés étrangères (*_id)
                        if field_info["type"] == "number" and field_name.endswith('_id'):
                            # Déterminer la table liée
                            if 'unit' in field_name:
                                ref_table = "units"
                                ref_id = "unit_id"
                                ref_label = lambda x: f"#{x['unit_id']} - {x.get('name', 'N/A')}"
                            elif 'person' in field_name or 'owner' in field_name or 'declared_by' in field_name:
                                ref_table = "persons"
                                ref_id = "person_id"
                                ref_label = lambda x: f"#{x['person_id']} - {x.get('name', '')} {x.get('family_name', '')}".strip()
                            elif 'risk' in field_name:
                                ref_table = "risks"
                                ref_id = "risk_id"
                                ref_label = lambda x: f"#{x['risk_id']} - {x.get('name', 'N/A')}"
                            else:
                                # Fallback: input numérique normal
                                form_data[field_name] = st.number_input(
                                    field_info["label"],
                                    value=int(current_value) if current_value is not None else 0,
                                    min_value=0,
                                    step=1,
                                    key=f"update_{field_name}"
                                )
                                continue
                            
                            # Charger les options
                            options = get_selector_options(ref_table)
                            if options:
                                options_dict = {opt[ref_id]: ref_label(opt) for opt in options}
                                # Trouver l'index de la valeur actuelle
                                current_index = 0
                                if current_value and current_value in options_dict:
                                    current_index = list(options_dict.keys()).index(current_value)
                                
                                selected_id_val = st.selectbox(
                                    field_info["label"],
                                    list(options_dict.keys()),
                                    format_func=lambda x: options_dict[x],
                                    index=current_index,
                                    key=f"update_{field_name}"
                                )
                                form_data[field_name] = selected_id_val
                            else:
                                st.warning(f"⚠️ Aucune donnée disponible pour {ref_table}")
                                form_data[field_name] = st.number_input(
                                    field_info["label"],
                                    value=int(current_value) if current_value is not None else 0,
                                    min_value=0,
                                    step=1,
                                    key=f"update_{field_name}"
                                )
                        
                        # Sélecteurs pour type et classification dans events
                        elif selected_table == "events" and field_name == "type":
                            if event_types:
                                # Vérifier si la valeur actuelle est dans la liste
                                if current_value in event_types:
                                    type_index = event_types.index(current_value)
                                    all_types = event_types + ["[Autre]"]
                                else:
                                    # Valeur personnalisée existante
                                    all_types = event_types + [current_value, "[Autre]"]
                                    type_index = len(event_types)
                                
                                col_type, col_custom = st.columns([3, 1])
                                with col_type:
                                    selected_type = st.selectbox(
                                        field_info["label"],
                                        all_types,
                                        index=type_index,
                                        key=f"update_{field_name}_select"
                                    )
                                with col_custom:
                                    if selected_type == "[Autre]":
                                        custom_type = st.text_input(
                                            "Type personnalisé",
                                            value=current_value if current_value not in event_types else "",
                                            key=f"update_{field_name}_custom"
                                        )
                                        form_data[field_name] = custom_type
                                    else:
                                        form_data[field_name] = selected_type
                                        st.markdown("<br>", unsafe_allow_html=True)
                            else:
                                form_data[field_name] = st.text_input(
                                    field_info["label"],
                                    value=current_value if current_value is not None else "",
                                    key=f"update_{field_name}"
                                )
                        
                        elif selected_table == "events" and field_name == "classification":
                            if event_classifications:
                                # Vérifier si la valeur actuelle est dans la liste
                                if current_value in event_classifications:
                                    class_index = event_classifications.index(current_value)
                                    all_classes = event_classifications + ["[Autre]"]
                                else:
                                    # Valeur personnalisée existante
                                    all_classes = event_classifications + [current_value, "[Autre]"]
                                    class_index = len(event_classifications)
                                
                                col_class, col_custom = st.columns([3, 1])
                                with col_class:
                                    selected_class = st.selectbox(
                                        field_info["label"],
                                        all_classes,
                                        index=class_index,
                                        key=f"update_{field_name}_select"
                                    )
                                with col_custom:
                                    if selected_class == "[Autre]":
                                        custom_class = st.text_input(
                                            "Classification personnalisée",
                                            value=current_value if current_value not in event_classifications else "",
                                            key=f"update_{field_name}_custom"
                                        )
                                        form_data[field_name] = custom_class
                                    else:
                                        form_data[field_name] = selected_class
                                        st.markdown("<br>", unsafe_allow_html=True)
                            else:
                                form_data[field_name] = st.text_input(
                                    field_info["label"],
                                    value=current_value if current_value is not None else "",
                                    key=f"update_{field_name}"
                                )
                        
                        # Champs texte normaux
                        elif field_info["type"] == "text":
                            form_data[field_name] = st.text_input(
                                field_info["label"],
                                value=current_value if current_value is not None else "",
                                key=f"update_{field_name}"
                            )
                        elif field_info["type"] == "textarea":
                            form_data[field_name] = st.text_area(
                                field_info["label"],
                                value=current_value if current_value is not None else "",
                                height=100,
                                key=f"update_{field_name}"
                            )
                        elif field_info["type"] == "number":
                            form_data[field_name] = st.number_input(
                                field_info["label"],
                                value=float(current_value) if current_value is not None else 0.0,
                                key=f"update_{field_name}"
                            )
                        elif field_info["type"] == "datetime":
                            if current_value:
                                try:
                                    dt_value = pd.to_datetime(current_value)
                                    col_date, col_time = st.columns(2)
                                    with col_date:
                                        date_value = st.date_input(
                                            f"{field_info['label']} - Date",
                                            value=dt_value.date(),
                                            key=f"update_{field_name}_date"
                                        )
                                    with col_time:
                                        time_value = st.time_input(
                                            f"{field_info['label']} - Heure",
                                            value=dt_value.time(),
                                            key=f"update_{field_name}_time"
                                        )
                                    form_data[field_name] = datetime.combine(date_value, time_value).isoformat()
                                except:
                                    form_data[field_name] = st.text_input(
                                        field_info["label"],
                                        value=current_value,
                                        key=f"update_{field_name}"
                                    )
                            else:
                                col_date, col_time = st.columns(2)
                                with col_date:
                                    date_value = st.date_input(
                                        f"{field_info['label']} - Date",
                                        key=f"update_{field_name}_date"
                                    )
                                with col_time:
                                    time_value = st.time_input(
                                        f"{field_info['label']} - Heure",
                                        key=f"update_{field_name}_time"
                                    )
                                form_data[field_name] = datetime.combine(date_value, time_value).isoformat()
                    
                    if st.button("💾 Enregistrer les modifications", type="primary", use_container_width=True):
                        # Valider les champs requis
                        missing_fields = [fields[k]["label"] for k, v in fields.items() 
                                        if v.get("required") and not form_data.get(k)]
                        
                        if missing_fields:
                            st.error(f"❌ Champs requis manquants: {', '.join(missing_fields)}")
                        else:
                            try:
                                update_response = requests.put(
                                    f"{BASE_URL}/{selected_table}/{selected_id}",
                                    json=form_data,
                                    timeout=5
                                )
                                if update_response.status_code == 200:
                                    st.success(f"✅ Enregistrement #{selected_id} modifié avec succès !")
                                    st.balloons()
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(f"❌ Erreur: {update_response.status_code} - {update_response.text}")
                            except Exception as e:
                                st.error(f"❌ Erreur: {str(e)}")
                else:
                    st.info("Aucun enregistrement trouvé dans cette table")
            else:
                st.error(f"❌ Erreur lors de la récupération des données: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")
    
    # CREATE
    elif action_type == "CREATE":
        st.markdown(f"### ➕ Créer un nouvel enregistrement dans {table_options[selected_table]}")
        
        # Charger les options pour les sélecteurs
        @st.cache_data(ttl=60)
        def get_selector_options(table_name):
            """Récupère les données d'une table pour les sélecteurs"""
            try:
                resp = requests.get(f"{BASE_URL}/{table_name}/", params={"limit": 1000}, timeout=5)
                if resp.status_code == 200:
                    return resp.json()
            except:
                pass
            return []
        
        # Charger les catégories existantes pour type et classification
        event_types = []
        event_classifications = []
        if selected_table == "events":
            all_events = get_selector_options("events")
            if all_events:
                event_types = sorted(list(set([e.get('type') for e in all_events if e.get('type')])))
                event_classifications = sorted(list(set([e.get('classification') for e in all_events if e.get('classification')])))
        
        form_data = {}
        
        for field_name, field_info in fields.items():
            if field_info.get("readonly", False):
                continue
            
            # Sélecteurs pour les clés étrangères (*_id)
            if field_info["type"] == "number" and field_name.endswith('_id'):
                # Déterminer la table liée
                if 'unit' in field_name:
                    ref_table = "units"
                    ref_id = "unit_id"
                    ref_label = lambda x: f"#{x['unit_id']} - {x.get('name', 'N/A')}"
                elif 'person' in field_name or 'owner' in field_name or 'declared_by' in field_name:
                    ref_table = "persons"
                    ref_id = "person_id"
                    ref_label = lambda x: f"#{x['person_id']} - {x.get('name', '')} {x.get('family_name', '')}".strip()
                elif 'risk' in field_name:
                    ref_table = "risks"
                    ref_id = "risk_id"
                    ref_label = lambda x: f"#{x['risk_id']} - {x.get('name', 'N/A')}"
                else:
                    # Fallback: input numérique normal
                    form_data[field_name] = st.number_input(
                        f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                        value=0,
                        min_value=0,
                        step=1,
                        key=f"create_{field_name}"
                    )
                    continue
                
                # Charger les options
                options = get_selector_options(ref_table)
                if options:
                    options_dict = {opt[ref_id]: ref_label(opt) for opt in options}
                    selected_id = st.selectbox(
                        f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                        list(options_dict.keys()),
                        format_func=lambda x: options_dict[x],
                        key=f"create_{field_name}"
                    )
                    form_data[field_name] = selected_id
                else:
                    st.warning(f"⚠️ Aucune donnée disponible pour {ref_table}")
                    form_data[field_name] = st.number_input(
                        f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                        value=0,
                        min_value=0,
                        step=1,
                        key=f"create_{field_name}"
                    )
            
            # Sélecteurs pour type et classification dans events
            elif selected_table == "events" and field_name == "type":
                if event_types:
                    col_type, col_custom = st.columns([3, 1])
                    with col_type:
                        selected_type = st.selectbox(
                            f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                            event_types + ["[Autre]"],
                            key=f"create_{field_name}_select"
                        )
                    with col_custom:
                        if selected_type == "[Autre]":
                            custom_type = st.text_input(
                                "Type personnalisé",
                                key=f"create_{field_name}_custom"
                            )
                            form_data[field_name] = custom_type
                        else:
                            form_data[field_name] = selected_type
                            st.markdown("<br>", unsafe_allow_html=True)
                else:
                    form_data[field_name] = st.text_input(
                        f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                        key=f"create_{field_name}"
                    )
            
            elif selected_table == "events" and field_name == "classification":
                if event_classifications:
                    col_class, col_custom = st.columns([3, 1])
                    with col_class:
                        selected_class = st.selectbox(
                            f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                            event_classifications + ["[Autre]"],
                            key=f"create_{field_name}_select"
                        )
                    with col_custom:
                        if selected_class == "[Autre]":
                            custom_class = st.text_input(
                                "Classification personnalisée",
                                key=f"create_{field_name}_custom"
                            )
                            form_data[field_name] = custom_class
                        else:
                            form_data[field_name] = selected_class
                            st.markdown("<br>", unsafe_allow_html=True)
                else:
                    form_data[field_name] = st.text_input(
                        f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                        key=f"create_{field_name}"
                    )
            
            # Champs texte normaux
            elif field_info["type"] == "text":
                form_data[field_name] = st.text_input(
                    f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                    key=f"create_{field_name}"
                )
            elif field_info["type"] == "textarea":
                # Module d'analyse d'image uniquement pour la description des événements
                if selected_table == "events" and field_name == "description":
                    st.markdown("---")
                    st.markdown("#### 📸 Analyse d'image (optionnel)")
                    st.markdown("Téléchargez une image de l'événement pour générer automatiquement une description avec l'IA")
                    
                    # Initialiser la session state pour la description AI
                    if "ai_generated_description" not in st.session_state:
                        st.session_state.ai_generated_description = ""
                    if "use_ai_description" not in st.session_state:
                        st.session_state.use_ai_description = False
                    
                    uploaded_image = st.file_uploader(
                        "Choisir une image",
                        type=["jpg", "jpeg", "png"],
                        key="event_image_uploader",
                        help="Formats acceptés : JPG, JPEG, PNG"
                    )
                    
                    if uploaded_image is not None:
                        # Afficher l'image en taille réduite
                        col_img, col_btn = st.columns([3, 2])
                        with col_img:
                            image = Image.open(uploaded_image)
                            st.image(image, caption="Image téléchargée", width=300)
                        
                        with col_btn:
                            st.write("")  # Espacement
                            if st.button("🤖 Analyser avec Gemini", type="secondary", use_container_width=True, key="analyze_image_btn"):
                                with st.spinner("🔍 Analyse de l'image en cours..."):
                                    # Réinitialiser le pointeur du fichier
                                    uploaded_image.seek(0)
                                    description, error = analyze_event_image_with_gemini(uploaded_image)
                                    
                                    if error:
                                        st.error(error)
                                        st.session_state.ai_generated_description = ""
                                    else:
                                        st.session_state.ai_generated_description = description
                                        st.success("✅ Description générée avec succès !")
                                        st.rerun()
                        
                        # Afficher la description générée si elle existe
                        if st.session_state.ai_generated_description:
                            st.markdown("**📝 Description générée par l'IA :**")
                            
                            # CSS pour rendre le bouton de copie plus visible
                            st.markdown("""
                            <style>
                            .stCodeBlock button[title="Copy to clipboard"] {
                                background-color: #4CAF50 !important;
                                color: white !important;
                                padding: 8px 16px !important;
                                border-radius: 6px !important;
                                font-size: 16px !important;
                                font-weight: bold !important;
                                border: 2px solid #45a049 !important;
                            }
                            .stCodeBlock button[title="Copy to clipboard"]:hover {
                                background-color: #45a049 !important;
                                transform: scale(1.05);
                            }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            # Afficher la description dans une zone copiable
                            st.code(st.session_state.ai_generated_description, language=None)
                    
                    st.markdown("---")
                
                form_data[field_name] = st.text_area(
                    f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                    height=150,
                    key=f"create_{field_name}",
                    help="Saisissez ou collez la description de l'événement"
                )
            elif field_info["type"] == "number":
                form_data[field_name] = st.number_input(
                    f"{field_info['label']}" + (" *" if field_info.get("required") else ""),
                    value=0.0,
                    key=f"create_{field_name}"
                )
            elif field_info["type"] == "datetime":
                col_date, col_time = st.columns(2)
                with col_date:
                    date_value = st.date_input(
                        f"{field_info['label']} - Date" + (" *" if field_info.get("required") else ""),
                        key=f"create_{field_name}_date"
                    )
                with col_time:
                    time_value = st.time_input(
                        f"{field_info['label']} - Heure" + (" *" if field_info.get("required") else ""),
                        key=f"create_{field_name}_time"
                    )
                form_data[field_name] = datetime.combine(date_value, time_value).isoformat()
        
        st.markdown("*\* Champs obligatoires*")
        
        if st.button("➕ Créer l'enregistrement", type="primary", use_container_width=True):
            # Valider les champs requis
            missing_fields = [fields[k]["label"] for k, v in fields.items() 
                            if v.get("required") and not form_data.get(k)]
            
            if missing_fields:
                st.error(f"❌ Champs requis manquants: {', '.join(missing_fields)}")
            else:
                try:
                    create_response = requests.post(
                        f"{BASE_URL}/{selected_table}/",
                        json=form_data,
                        timeout=5
                    )
                    if create_response.status_code == 201:
                        new_record = create_response.json()
                        created_id = new_record.get(id_field)
                        
                        # Nettoyer la session state (description AI)
                        if "ai_generated_description" in st.session_state:
                            del st.session_state.ai_generated_description
                        if "use_ai_description" in st.session_state:
                            del st.session_state.use_ai_description
                        
                        # Afficher l'ID créé en grand
                        st.success(f"✅ Enregistrement créé avec succès !")
                        st.markdown(f"### 🎯 ID créé: **{created_id}**")
                        st.balloons()
                        
                        # Afficher les détails
                        with st.expander("📋 Détails du nouvel enregistrement", expanded=True):
                            st.json(new_record)
                        
                        # Invalider le cache
                        st.cache_data.clear()
                    else:
                        st.error(f"❌ Erreur: {create_response.status_code} - {create_response.text}")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

# Footer
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align: center; color: #94a3b8; padding: 2rem 0; font-size: 0.875rem;'>
    <p>Safety Analytics Dashboard | Powered by Streamlit & Plotly</p>
</div>
""", unsafe_allow_html=True)
