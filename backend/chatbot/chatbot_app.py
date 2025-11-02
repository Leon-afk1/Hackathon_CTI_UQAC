"""
Application Streamlit pour un chatbot RAG utilisant Gemini
avec accès à la base de données PostgreSQL d'événements.

AMÉLIORATIONS v2.2:
- ✅ Parser custom pour le format data_retriever (### Résultat X: - key: value)
- ✅ Gestion robuste des cas sans données (propose alternatives au lieu de crasher)
- ✅ Mémoire optimisée: priorité ABSOLUE au dernier prompt (3 derniers échanges max)
- ✅ Directives claires au LLM: ne génère du code QUE si données valides
- ✅ Détection améliorée des nouvelles questions indépendantes
- ✅ Validation des données avant génération de graphiques
- ✅ Messages d'erreur plus clairs et instructifs
- ✅ Debug info (aperçu données, code qui échoue, etc.)
- ✅ Extraction de code améliorée (multiples patterns, validation)
- ✅ **NETTOYAGE AUTO DES IMPORTS** - Retire les imports interdits du code généré
- ✅ **NAMESPACE ÉTENDU** - Builtins complets (True, False, None, isinstance, etc.)
- ✅ **DIRECTIVES RENFORCÉES** - Indique explicitement de NE PAS importer
"""

import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from data_retriever import data_retriever
from memory_utils import prepare_context_for_sql
from pdf_generator import detect_pdf_request, generate_professional_pdf
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import re
import json
from io import StringIO
from datetime import datetime

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant Gestion d'Événements",
    page_icon="🛡️",
    layout="wide"
)

# CSS pour un bouton fixe en haut à droite
st.markdown("""
<style>
    .stButton button[kind="secondary"] {
        position: fixed;
        top: 70px;
        right: 20px;
        z-index: 999999;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        font-size: 24px;
        padding: 0;
        background-color: #ff4b4b;
        color: white;
        border: 2px solid white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .stButton button[kind="secondary"]:hover {
        background-color: #ff6b6b;
        transform: scale(1.1);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Style pour les boutons de suggestions */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 20px;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    .stButton button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Style alternatif pour suggestions de base */
    div[data-testid="column"] > div > div > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 16px;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s ease;
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3);
        white-space: normal;
        height: auto;
        min-height: 50px;
    }
    
    div[data-testid="column"] > div > div > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4);
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    }
</style>
""", unsafe_allow_html=True)

# --- Configuration de l'API Gemini ---
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    st.error("⚠️ Clé API Gemini non trouvée. Définis GEMINI_API_KEY dans ton fichier .env")
    st.stop()

genai.configure(api_key=API_KEY)

# Initialisation du modèle
@st.cache_resource
def init_gemini_model():
    """Initialize le modèle Gemini avec fallback."""
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        return model, "gemini-2.5-flash"
    except Exception as e:
        st.warning(f"Erreur avec gemini-2.5-flash: {e}. Fallback vers gemini-pro.")
        try:
            model = genai.GenerativeModel('gemini-pro')
            return model, "gemini-pro"
        except Exception as e:
            st.error(f"Impossible d'initialiser un modèle Gemini: {e}")
            return None, None

model, model_name = init_gemini_model()

if model is None:
    st.stop()

# --- Fonction d'exécution sécurisée du code Plotly ---
def execute_plotly_code_safely(code: str, data_context: dict) -> tuple:
    """
    Exécute du code Python Plotly dans un environnement sécurisé.
    
    Args:
        code: Code Python à exécuter
        data_context: Dictionnaire contenant les données (df, etc.)
    
    Returns:
        (success: bool, result: plotly.graph_objs.Figure or error message)
    """
    # Validation du code
    forbidden_patterns = [
        r'\bos\b', r'\bsys\b', r'\bsubprocess\b', r'\beval\b', 
        r'\bexec\b', r'\b__import__\b', r'\bopen\b', r'\bfile\b',
        r'\bcompile\b', r'\bglobals\b', r'\blocals\b'
    ]
    
    for pattern in forbidden_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Code interdit détecté: {pattern}"
    
    # Imports autorisés
    safe_imports = {
        'plotly': __import__('plotly'),
        'px': px,
        'go': go,
        'pd': pd,
        'np': np,
        'json': json
    }
    
    # Namespace sécurisé avec builtins étendus
    safe_namespace = {
        '__builtins__': {
            'range': range,
            'len': len,
            'str': str,
            'int': int,
            'float': float,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'zip': zip,
            'enumerate': enumerate,
            'min': min,
            'max': max,
            'sum': sum,
            'abs': abs,
            'round': round,
            'sorted': sorted,
            'reversed': reversed,
            'map': map,
            'filter': filter,
            'any': any,
            'all': all,
            'isinstance': isinstance,
            'type': type,
            'bool': bool,
            'True': True,
            'False': False,
            'None': None,
        },
        **safe_imports,
        **data_context
    }
    
    try:
        # Exécution du code
        exec(code, safe_namespace)
        
        # Récupération de la figure
        if 'fig' in safe_namespace:
            return True, safe_namespace['fig']
        else:
            return False, "Aucune variable 'fig' trouvée dans le code"
    
    except Exception as e:
        return False, f"Erreur d'exécution: {str(e)}"


def extract_code_from_response(text: str) -> str:
    """Extrait le code Python d'une réponse Gemini et nettoie les imports."""
    # Cherche les blocs de code Python (plusieurs patterns possibles)
    patterns = [
        r'```python\n(.*?)```',
        r'```python\s+(.*?)```',
        r'```py\n(.*?)```',
        r'```\n(.*?)```',
    ]
    
    code = ""
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            # Vérifier que c'est bien du code Python (contient fig)
            if 'fig' in code or 'px.' in code or 'go.' in code:
                break
    
    # Si aucun bloc trouvé mais le texte contient du code apparent
    if not code and ('fig =' in text or 'px.' in text or 'go.' in text):
        code = text.strip()
    
    if not code:
        return ""
    
    # Nettoyer le code: retirer les imports interdits
    lines = code.split('\n')
    cleaned_lines = []
    removed_imports = []
    
    for line in lines:
        line_stripped = line.strip()
        # Ignorer les imports
        if (line_stripped.startswith('import ') or 
            line_stripped.startswith('from ') or
            ('import' in line_stripped and ('plotly' in line_stripped or 'pandas' in line_stripped or 'numpy' in line_stripped))):
            removed_imports.append(line_stripped)
            continue  # Sauter cette ligne
        cleaned_lines.append(line)
    
    cleaned_code = '\n'.join(cleaned_lines).strip()
    
    # Log si on a retiré des imports (pour debug)
    if removed_imports:
        import streamlit as st
        st.info(f"🧹 {len(removed_imports)} import(s) automatiquement retirés (déjà disponibles)")
    
    return cleaned_code


# Prompt système pour le chatbot
SYSTEM_PROMPT = """Tu es un expert en analyse d'événements. Réponds de manière SYNTHÉTIQUE et RAPIDE.

## BASE DE DONNÉES
- event (événements centraux)
- person (employés)
- risk (risques)  
- corrective_measure (actions)
- organizational_unit (services)
- Tables liaison: event_employee, event_risk, event_corrective_measure

## RÈGLES ABSOLUES

### 1. PAS DE DONNÉES = PAS DE GRAPHIQUE
Si les données sont vides, "Aucune donnée", ou insuffisantes:
-  NE génère PAS de code Python
-  Explique pourquoi (ex: "Aucun événement trouvé pour ces critères")
-  Propose une alternative concrète

**Exemple CORRECT:**
```
Aucun événement trouvé pour octobre 2025.

 Alternatives:
- "Événements récents" (tous types)
- "Événements de septembre 2025"
- "Liste de tous les événements"
```

### 2. QUAND FAIRE UN GRAPHIQUE ? (RÈGLE CRITIQUE)
🚨 **NE génère un graphique QUE si l'utilisateur demande EXPLICITEMENT une visualisation**

**Demandes qui NÉCESSITENT un graphique:**
- "Fais un graphique de..."
- "Visualise..."
- "Montre-moi un graphe..."
- "Crée un diagramme..."
- "Graphe des..."
- "Répartition en secteurs..."
- "Évolution au fil du temps..."

**Demandes qui NE NÉCESSITENT PAS de graphique (réponds juste avec du texte/tableau):**
- "Donne-moi des informations sur l'événement 875"
- "Quel est le statut de..."
- "Liste les événements..."
- "Montre-moi les détails de..."
- "Quels sont les risques associés à..."
- "Qui est impliqué dans..."

**EXEMPLES CONCRETS:**

❌ **MAUVAIS** (pas de graphique demandé):
Question: "Donne-moi des informations sur l'événement 875"
→ Ne génère PAS de code Python, réponds avec un tableau/texte

✅ **BON** (graphique demandé):
Question: "Fais un graphique des événements par mois"
→ Génère le code Python Plotly

❌ **MAUVAIS** (pas de graphique demandé):
Question: "Liste les 10 derniers événements"
→ Ne génère PAS de code Python, affiche juste un tableau

✅ **BON** (graphique demandé):
Question: "Visualise la répartition des types d'événements"
→ Génère le code Python Plotly

### 3. STYLE DE RÉPONSE
1. **VA DROIT AU BUT** - L'utilisateur veut une info rapide
2. **SYNTHÉTISE** - Résume, n'étale pas sauf si on de le demande explicitement
3. **STRUCTURE** - Tableaux courts, puces, chiffres clés
4. **EXPLIQUE** - Dis ce que tu as trouvé et pourquoi c'est important
5. **SOIS PRÉCIS** - Cite les IDs, noms, chiffres exacts

## EXEMPLES

 MAL: "Bien sûr ! Je suis ravi de vous aider. Voici une liste exhaustive de tous les événements..."

 BIEN: "**5 événements récents:**
| ID | Description | Date | Type |
|---|---|---|---|
| 125 | Panne ligne A | 28/10 | Incident |
 3 sont critiques, 2 résolus"

## TON APPROCHE
- Commence direct (pas de "bien sûr, je serais ravi...")
- Mets les chiffres importants en avant
- Propose une action si pertinent
- **Si pas de données: EXPLIQUE pourquoi + propose 2-3 alternatives**

## GRAPHIQUES INTERACTIFS

### AVANT DE GÉNÉRER DU CODE:
1. **VÉRIFIE D'ABORD LA QUESTION** : L'utilisateur demande-t-il explicitement un graphique/visualisation ?
2. Si NON → Réponds avec texte/tableau seulement, PAS de code Python
3. Si OUI → Vérifie que les données existent et sont valides
4. Si pas de données valides → NE génère PAS de code, propose alternative

**EXEMPLES DE DÉCISIONS:**

Question: "Donne-moi des informations sur l'événement 875"
→ 🚫 PAS de graphique (juste info demandée)
→ Réponds: Tableau avec détails de l'événement 875

Question: "Liste les événements critiques"
→ 🚫 PAS de graphique (liste demandée)
→ Réponds: Tableau avec liste des événements

Question: "Fais un graphique des événements par type"
→ ✅ GRAPHIQUE demandé
→ Génère: Code Python Plotly avec px.bar() ou px.pie()

Question: "Visualise l'évolution des incidents"
→ ✅ GRAPHIQUE demandé (visualise = graphique)
→ Génère: Code Python Plotly avec px.line()

### RÈGLES CODE (si graphique demandé ET données OK):

**RÈGLES CRITIQUES - À RESPECTER ABSOLUMENT:**
1. **N'IMPORTE RIEN** - Les modules sont DÉJÀ disponibles (px, go, pd, np, df)
2. **PAS DE `import plotly` ou `import pandas`** - Tout est déjà importé !
3. Utilise directement `px.bar()`, `go.Figure()`, `df.head()`, etc.
4. La variable finale DOIT être `fig`
5. Vérifie les colonnes avec `if 'colonne' in df.columns`

**TEMPLATE CORRECT (SANS IMPORT):**
```python
# Vérifier que df contient des données
if df.empty or 'colonne_x' not in df.columns:
    # Créer des données d'exemple
    df = pd.DataFrame({
        'colonne_x': ['A', 'B', 'C'],
        'colonne_y': [10, 20, 15]
    })

# Créer le graphique (px et go sont déjà disponibles)
fig = px.bar(df, x='colonne_x', y='colonne_y', 
             title='Titre clair',
             color_discrete_sequence=['#3b82f6'])

fig.update_layout(
    template='plotly_white',
    font=dict(family='Inter, sans-serif', size=12),
    title_font_size=16,
    showlegend=True
)
```

**NE FAIS PAS:**
```python
import plotly.express as px  # INTERDIT
import pandas as pd           # INTERDIT
from plotly import graph_objects as go  # INTERDIT
```

**TYPES COURANTS:**
- Barres: `px.bar()` 
- Lignes: `px.line()`
- Secteurs: `px.pie()`
- Scatter: `px.scatter()`

### DÉCISION FINALE:
- Question demande visualisation + données valides → Génère code Python (dans ```python)
- Question demande juste info/liste → TEXTE/TABLEAU seulement (PAS de code)
- Pas de données ou données insuffisantes → EXPLIQUE + propose alternatives (PAS de code)
"""

# --- Interface Streamlit ---

# Bouton de réinitialisation fixe (en haut à droite)
if st.button("🔄", help="Réinitialiser la conversation", type="secondary", key="reset_button"):
    st.session_state.messages = []
    st.session_state.conversation_history = []  # Nettoyer aussi la mémoire
    st.rerun()

# En-tête
st.title("🛡️ Assistant Gestion d'Événements & Risques")
st.markdown(f"*Propulsé par {model_name}*")

# Initialisation de l'historique des messages et de la conversation
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome_message = """### 👋 Assistant Événements

Je réponds rapidement à vos questions sur:
- 📋 Événements & incidents
- ⚠️ Risques  
- ✅ Mesures correctives
- 👥 Personnes impliquées

**Pose ta question ou sélectionne une suggestion ci-dessous !** 🚀
"""
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome_message
    })

# Initialisation de l'historique de conversation (pour mémoire SQL)
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Initialisation d'une variable pour gérer les suggestions cliquées
if "selected_suggestion" not in st.session_state:
    st.session_state.selected_suggestion = None

# Affichage de l'historique des messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Afficher le contenu texte d'abord
        if "content" in message:
            st.markdown(message["content"])
        
        # Si le message contient un graphique (figure plotly sauvegardée)
        if "chart" in message:
            st.plotly_chart(message["chart"], use_container_width=True)

# ========= SUGGESTIONS DE QUESTIONS (au début ou après réponse) =========
def show_question_suggestions():
    """Affiche des boutons de suggestions de questions"""
    
    # Suggestions selon le contexte
    if len(st.session_state.messages) <= 1:
        # Suggestions initiales (au démarrage)
        suggestions = [
            "📊 Donne-moi un aperçu des événements récents",
            "⚠️ Quels sont les risques les plus critiques ?",
            "📈 Fais un graphique des événements par type",
            "👥 Liste les personnes les plus impliquées",
            "📅 Visualise l'évolution des événements par mois",
            "🏢 Quelles sont les unités avec le plus d'incidents ?"
        ]
        st.markdown("### 💡 Questions suggérées")
    else:
        # Suggestions basées sur la dernière question
        last_message = st.session_state.messages[-1].get("content", "")
        
        # Déterminer le contexte
        if "événement" in last_message.lower() or "incident" in last_message.lower():
            suggestions = [
                "📊 Fais un graphique de ces événements",
                "⚠️ Quels sont les risques associés ?",
                "✅ Quelles mesures correctives ont été prises ?",
                "👥 Qui sont les personnes impliquées ?"
            ]
        elif "risque" in last_message.lower():
            suggestions = [
                "📋 Liste les événements liés à ces risques",
                "📈 Visualise la répartition de ces risques",
                "🏢 Quelles unités sont les plus concernées ?"
            ]
        elif "mesure" in last_message.lower() or "corrective" in last_message.lower():
            suggestions = [
                "📊 Fais un graphique des mesures par statut",
                "📋 Liste les événements concernés",
                "👥 Qui sont les responsables ?"
            ]
        else:
            suggestions = [
                "📊 Fais un graphique de ces données",
                "📋 Donne-moi plus de détails",
                "📈 Montre-moi l'évolution dans le temps",
                "🔍 Analyse plus approfondie"
            ]
        
        st.markdown("### 💡 Questions de suivi suggérées")
    
    # Créer une grille de boutons (3 colonnes)
    cols = st.columns(3)
    for idx, suggestion in enumerate(suggestions):
        col = cols[idx % 3]
        with col:
            if st.button(suggestion, key=f"suggestion_{idx}", use_container_width=True):
                st.session_state.selected_suggestion = suggestion
                st.rerun()

# Afficher les suggestions avant la zone de saisie
show_question_suggestions()

# Zone de saisie utilisateur
prompt = st.chat_input("Posez votre question sur les événements, risques ou mesures...")

# Si une suggestion a été cliquée, l'utiliser comme prompt
if st.session_state.selected_suggestion:
    prompt = st.session_state.selected_suggestion
    st.session_state.selected_suggestion = None  # Réinitialiser

if prompt:
    # Ajout du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # ======= DÉTECTION DE DEMANDE DE PDF =======
    if detect_pdf_request(prompt):
        with st.chat_message("assistant"):
            st.markdown("### 📄 Génération du rapport PDF en cours...")
            
            if len(st.session_state.messages) < 3:
                response_text = """❌ **Impossible de générer un rapport**
                
Il n'y a pas encore assez de conversation pour créer un rapport significatif.
Pose d'abord quelques questions sur les événements, risques ou mesures, puis je pourrai générer 
un rapport professionnel avec des recommandations personnalisées ! 🚀"""
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            else:
                try:
                    # Générer le PDF
                    pdf_buffer = generate_professional_pdf(st.session_state.messages, model)
                    
                    # Créer un nom de fichier avec timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"Rapport_Evenements_{timestamp}.pdf"
                    
                    response_text = f"""✅ **Rapport de synthèse généré avec succès !**
                    
📊 **Format du rapport:**
- 📝 Introduction contextuelle
- 🔍 Analyse thématique narrative
- 📈 Visualisations des données clés
- 💡 Observations et insights
- 🎯 Recommandations stratégiques actionnables

💼 **Style professionnel** : Rédigé comme un rapport d'analyste humain, sans format "Question/Réponse"

📥 **Télécharge ton rapport ci-dessous:**"""
                    
                    st.markdown(response_text)
                    
                    # Bouton de téléchargement
                    st.download_button(
                        label="📄 Télécharger le rapport de synthèse",
                        data=pdf_buffer,
                        file_name=filename,
                        mime="application/pdf",
                        use_container_width=True,
                        type="primary"
                    )
                    
                    st.success("✨ Rapport narratif professionnel prêt à partager !")
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_text
                    })
                    
                except Exception as e:
                    error_msg = f"""❌ **Erreur lors de la génération du PDF**
                    
Détails: {str(e)}

Essaie de poser d'autres questions d'abord, puis redemande un rapport."""
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
        
        st.stop()  # Arrêter ici pour ne pas continuer le traitement normal
    
    # ======= TRAITEMENT NORMAL DE LA QUESTION =======
    # Génération de la réponse
    with st.chat_message("assistant"):
        # Afficher un indicateur si on utilise l'historique
        history_size = len(st.session_state.conversation_history)
        if history_size > 0:
            with st.expander(f"🧠 Mémoire active: {history_size} échange(s) précédent(s)", expanded=False):
                for i, ex in enumerate(st.session_state.conversation_history[-3:], 1):
                    st.caption(f"{i}. Q: {ex.get('question', 'N/A')[:60]}...")
        
        with st.spinner("🔍 Analyse de la question et génération de la requête SQL..."):
            # Préparer le contexte (synthèse si trop long, vide si question non liée)
            # PRIORITÉ: On ne garde que les 3 derniers échanges max
            prepared_history = prepare_context_for_sql(
                st.session_state.conversation_history[-3:],  # Seulement les 3 derniers
                prompt
            )
            
            # Afficher si la mémoire est utilisée ou non
            if not prepared_history and history_size > 0:
                st.info("💡 Question indépendante détectée - Contexte réinitialisé")
            elif prepared_history and len(prepared_history) < len(st.session_state.conversation_history[-3:]):
                st.info(f"🔄 Mémoire optimisée: Focus sur les {len(prepared_history)} derniers échanges pertinents")
            
            # Récupération du contexte depuis la base de données avec SQL intelligent
            search_result = data_retriever.search_relevant_data(
                prompt, 
                prepared_history
            )
            schema = data_retriever.get_database_schema()
            
            # Extraction des informations du résultat
            context = search_result.get('context', 'Aucune donnée')
            sql_used = search_result.get('sql_used')
            explanation = search_result.get('explanation', '')
            success = search_result.get('success', False)
            row_count = search_result.get('row_count', 0)
        
        # Affichage d'informations sur la requête
        attempts = search_result.get('attempts', 1)
        if success and sql_used:
            attempt_msg = f" (1ère tentative)" if attempts == 1 else f" (tentative {attempts}/5)"
            st.success(f"✅ Requête exécutée avec succès{attempt_msg} - {row_count} résultat(s) trouvé(s)")
        elif not success:
            if attempts >= 5:
                st.error(f"❌ Échec après {attempts} tentatives - Abandon de la génération SQL")
                st.info("💡 Conseil: Reformule ta question de manière plus précise ou utilise des IDs exacts")
            else:
                attempt_msg = f" après {attempts} tentative(s)" if attempts > 1 else ""
                st.warning(f"⚠️ Échec{attempt_msg} - {search_result.get('error', 'Erreur inconnue')}")
        
        with st.spinner("🤔 Génération de la réponse intelligente..."):
            # Construction du prompt complet
            full_prompt = f"""{SYSTEM_PROMPT}

## Schéma de la base de données:
{schema}

## Contexte récupéré depuis la base de données:
{context}

## ⚠️ ANALYSE AVANT DE RÉPONDRE:

### ÉTAPE 1: La question demande-t-elle un graphique ?
- Mots-clés graphique: "graphique", "visualise", "graphe", "diagramme", "évolution", "répartition"
- Si AUCUN de ces mots → Réponds avec TEXTE/TABLEAU seulement (PAS de code Python)
- Si présents → Passe à l'étape 2

### ÉTAPE 2: Y a-t-il des données ?
- Vérifie si le contexte contient des données réelles ou juste "Aucune donnée"
- Si pas de données → NE génère PAS de graphique, explique pourquoi + propose alternatives
- Si données présentes ET graphique demandé → Génère le code Python

## Question utilisateur (PRIORITÉ ABSOLUE):
{prompt}

## FORMAT RÉPONSE:

### CAS 1: QUESTION D'INFORMATION (ex: "Donne-moi des infos sur l'événement 875")
→ Réponds avec un tableau détaillé, PAS de code Python

**EXEMPLE:**
```
**Événement #875**

| Champ | Valeur |
|---|---|
| Description | Panne électrique |
| Date | 15/10/2024 |
| Statut | Résolu |
| Gravité | Moyenne |

💡 Résolu en 3h, aucune blessure
```

### CAS 2: DEMANDE DE LISTE (ex: "Liste les événements critiques")
→ Réponds avec un tableau, PAS de code Python

**EXEMPLE:**
```
**5 événements critiques:**

| ID | Description | Date | Statut |
|---|---|---|---|
| 125 | Panne ligne A | 28/10 | En cours |
| 124 | Chute escalier | 27/10 | Résolu |

💡 3 en cours, 2 résolus
```

### CAS 3: DEMANDE DE VISUALISATION (ex: "Fais un graphique des événements par type")
→ Génère du code Python Plotly (dans ```python)

**EXEMPLE:**
```
**Distribution des événements par type:**

```python
if df.empty:
    df = pd.DataFrame({
        'type': ['Incident', 'Accident', 'Anomalie'],
        'count': [45, 23, 12]
    })

fig = px.bar(df, x='type', y='count', 
             title='Événements par type',
             color_discrete_sequence=['#3b82f6'])
fig.update_layout(template='plotly_white')
```
```

### CAS 4: PAS DE DONNÉES
**STRUCTURE:**
1. Constat clair: "Aucun événement trouvé pour [critère]"
2. Raison probable (ex: "Aucun événement enregistré en octobre 2025")
3. 💡 **2-3 alternatives concrètes**

**EXEMPLE:**
```
Aucun événement trouvé pour octobre 2025.

💡 Essaye plutôt:
- "Événements récents" (tous mois confondus)
- "Événements de septembre 2025"
- "Liste complète des événements"
```

**RÈGLES FINALES:**
- Max 10 lignes de tableau
- Dates format court: JJ/MM
- Pas de phrases longues
- Mets en gras les chiffres importants
- Si >10 résultats: indique le total mais affiche que 10

**DÉCISION CODE PYTHON:**
- ✅ Génère du code UNIQUEMENT si:
  1. La question demande EXPLICITEMENT une visualisation (graphique/graphe/visualise/etc.)
  2. ET les données sont valides
- ❌ Ne génère PAS de code si:
  1. Question demande juste des informations/détails/liste
  2. OU pas de données disponibles
"""
            
            try:
                # Génération de la réponse avec Gemini
                response = model.generate_content(full_prompt)
                assistant_response = response.text
                
                # Détection si la réponse contient du code pour graphique
                chart_generated = False
                plotly_figure = None
                
                # Vérifier si on a des données valides (critères assouplis)
                has_valid_data = (context and 
                                 context.strip() and
                                 context != "Aucune donnée" and 
                                 len(context.strip()) > 20)  # Moins strict
                
                if "```python" in assistant_response or "```" in assistant_response:
                    # Si vraiment aucune donnée, on affiche juste le texte
                    if not context or context == "Aucune donnée" or len(context.strip()) < 10:
                        st.warning("⚠️ Pas de données disponibles pour générer un graphique")
                        text_only = re.sub(r'```python.*?```', '', assistant_response, flags=re.DOTALL)
                        text_only = re.sub(r'```.*?```', '', text_only, flags=re.DOTALL)
                        st.markdown(text_only.strip() if text_only.strip() else assistant_response)
                        # Pas de graphique généré, on continue normalement
                    else:
                        st.info("📊 Génération d'un graphique interactif...")
                        
                        # Extraction du code
                        code = extract_code_from_response(assistant_response)
                        
                        if not code:
                            st.warning("⚠️ Aucun code Python valide trouvé dans la réponse")
                            with st.expander("🔍 Debug: Voir la réponse brute"):
                                st.code(assistant_response, language="markdown")
                            # Afficher juste le texte sans code
                            text_only = re.sub(r'```.*?```', '', assistant_response, flags=re.DOTALL)
                            st.markdown(text_only.strip() if text_only.strip() else "Pas de texte explicatif trouvé")
                            code = None
                        
                        # Préparer les données pour l'exécution uniquement si on a du code
                        df = None
                        if code:
                            try:
                                # Tenter de parser le contexte comme données tabulaires
                                if context and context != "Aucune donnée":
                                    lines = context.strip().split('\n')
                                    
                                    if len(lines) > 1:
                                        # Parser le format spécifique du data_retriever
                                        # Format: "### Résultat X:\n  - colonne: valeur\n  - colonne: valeur"
                                        data_rows = []
                                        current_row = {}
                                        
                                        for line in lines:
                                            line = line.strip()
                                            if line.startswith('### Résultat'):
                                                # Nouveau résultat, sauvegarder le précédent
                                                if current_row:
                                                    data_rows.append(current_row)
                                                current_row = {}
                                            elif line.startswith('- ') or line.startswith('•'):
                                                # Extraire clé: valeur
                                                try:
                                                    key_value = line.lstrip('- •').strip()
                                                    if ':' in key_value:
                                                        key, value = key_value.split(':', 1)
                                                        current_row[key.strip()] = value.strip()
                                                except:
                                                    pass
                                        
                                        # Ajouter le dernier résultat
                                        if current_row:
                                            data_rows.append(current_row)
                                        
                                        # Créer le DataFrame
                                        if data_rows:
                                            df = pd.DataFrame(data_rows)
                                            
                                            # Convertir les types numériques si possible
                                            for col in df.columns:
                                                try:
                                                    df[col] = pd.to_numeric(df[col])
                                                except (ValueError, TypeError):
                                                    pass
                                            
                                            st.success(f"✅ DataFrame créé: {len(df)} lignes, {len(df.columns)} colonnes")
                                            with st.expander("🔍 Aperçu des données"):
                                                st.write(f"**Colonnes:** {', '.join(df.columns)}")
                                                st.dataframe(df.head(5))
                                        else:
                                            st.warning("⚠️ Aucune donnée structurée trouvée dans le contexte")
                                            df = pd.DataFrame()
                            except Exception as e:
                                st.error(f"❌ Erreur lors du parsing des données: {str(e)}")
                                with st.expander("🐛 Debug - Contexte reçu"):
                                    st.text(context[:1000])
                                # Si échec, créer un DataFrame vide
                                df = pd.DataFrame()
                            
                            # Tentative d'exécution avec retry (max 5 fois)
                            max_attempts = 5
                            current_code = code
                            
                            for attempt in range(1, max_attempts + 1):
                                # Exécuter le code
                                with st.spinner(f"Exécution du code (tentative {attempt}/{max_attempts})..."):
                                    success_code, result = execute_plotly_code_safely(current_code, {'df': df})
                                
                                if success_code and result is not None and hasattr(result, 'to_html'):
                                    # Succès !
                                    attempt_msg = "" if attempt == 1 else f" (tentative {attempt}/{max_attempts})"
                                    st.success(f"✅ Graphique créé avec succès !{attempt_msg}")
                                    
                                    # Afficher aussi le texte explicatif (sans le code)
                                    text_only = re.sub(r'```python.*?```', '', assistant_response, flags=re.DOTALL)
                                    if text_only.strip():
                                        st.markdown(text_only.strip())
                                    
                                    # Afficher le graphique après le texte
                                    st.plotly_chart(result, use_container_width=True)
                                    
                                    plotly_figure = result
                                    chart_generated = True
                                    break
                                else:
                                    # Échec - tenter de corriger
                                    if attempt < max_attempts:
                                        st.warning(f"⚠️ Tentative {attempt}/{max_attempts} échouée: {result}")
                                        
                                        # Créer un prompt de correction
                                        correction_prompt = f"""Le code Python Plotly suivant a produit une erreur:

```python
{current_code}
```

**Erreur:** {result}

**Données disponibles:** DataFrame 'df' avec colonnes: {list(df.columns) if df is not None and not df.empty else "DataFrame vide"}

Corrige le code pour qu'il fonctionne. Génère UNIQUEMENT le code Python corrigé dans un bloc ```python.

**RÈGLES CRITIQUES:**
- 🚨 N'IMPORTE RIEN - px, go, pd, np, df sont DÉJÀ disponibles
- 🚨 PAS de `import plotly` ou `import pandas` - INTERDIT !
- Variable finale doit être `fig`
- Vérifie que les colonnes existent dans df
- Si df vide, crée des données exemple
- Utilise directement px.bar(), go.Figure(), etc.
"""
                                        
                                        try:
                                            correction_response = model.generate_content(correction_prompt)
                                            current_code = extract_code_from_response(correction_response.text)
                                        except Exception as e:
                                            st.error(f"❌ Erreur lors de la correction: {str(e)}")
                                            break
                                    else:
                                        # Échec après 5 tentatives
                                        st.error(f"❌ Échec après {max_attempts} tentatives: {result}")
                                        with st.expander("🐛 Code qui a échoué"):
                                            st.code(current_code, language="python")
                                            if df is not None and not df.empty:
                                                st.markdown("**Données disponibles:**")
                                                st.dataframe(df.head())
                                        st.markdown(assistant_response)
                else:
                    # Affichage normal de la réponse
                    st.markdown(assistant_response)
                
                # Ajout à l'historique des messages (avec ou sans graphique)
                message_data = {
                    "role": "assistant",
                    "content": assistant_response
                }
                
                # Si un graphique a été généré, le sauvegarder dans l'historique
                if chart_generated and plotly_figure is not None:
                    message_data["chart"] = plotly_figure
                
                st.session_state.messages.append(message_data)
                
                # Ajout à l'historique de conversation (pour la mémoire SQL)
                # Extraire les informations clés de la réponse pour le contexte
                result_summary = context[:800] if context else ""  # Garde plus de contexte
                
                st.session_state.conversation_history.append({
                    "question": prompt,
                    "sql": sql_used if sql_used else "",
                    "result": result_summary,
                    "assistant_response": assistant_response[:300]  # Début de la réponse du chatbot
                })
                
                # Garde seulement les 5 derniers échanges (mémoire courte terme)
                if len(st.session_state.conversation_history) > 5:
                    st.session_state.conversation_history = st.session_state.conversation_history[-5:]
                
                # Affichage optionnel des détails techniques (dans un expander)
                with st.expander("🔍 Voir les détails techniques (SQL & données)"):
                    if sql_used:
                        st.markdown("### 📝 Requête SQL générée (formatée pour debug):")
                        st.code(sql_used, language="sql")
                        
                        # Afficher aussi la version raw si disponible
                        if 'sql_raw' in search_result and search_result['sql_raw'] != sql_used:
                            st.markdown("**Version compacte (exécutée):**")
                            st.code(search_result['sql_raw'], language="sql")
                        
                        if explanation:
                            st.markdown(f"**Explication:** {explanation}")
                        
                        if 'attempts' in search_result:
                            st.info(f"🔄 Nombre de tentatives: {search_result['attempts']}")
                    
                    st.markdown("### 📊 Données récupérées:")
                    st.text(context[:2000] + ("..." if len(context) > 2000 else ""))
                    
                    if not success:
                        if 'error' in search_result:
                            st.markdown("### ⚠️ Erreur:")
                            st.error(search_result['error'])
                        if 'traceback' in search_result:
                            st.markdown("**Trace complète:**")
                            st.code(search_result['traceback'], language="python")
                
            except Exception as e:
                error_msg = f"❌ Erreur lors de la génération de la réponse: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })

# Footer
st.markdown("---")
st.markdown("*💡 Conseil: Posez des questions précises pour obtenir les meilleures réponses.*")
