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
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import re
import json
from io import StringIO, BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Assistant Gestion d'Événements",
    page_icon="🛡️",
    layout="wide"
)

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

### 2. DONNÉES PRÉSENTES = GRAPHIQUE POSSIBLE
Si tu as des données tabulaires valides:
-  Génère le code Python Plotly
-  Vérifie que les colonnes nécessaires existent dans les données
-  Crée des données d'exemple si le DataFrame est vide

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
1. Vérifie que les données existent et sont valides
2. Vérifie que les colonnes nécessaires sont présentes
3. Si pas de données valides → NE génère PAS de code, propose alternative

### RÈGLES CODE (si données OK):

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
- Données valides + demande graphique → Génère code Python (dans ```python)
- Pas de données ou données insuffisantes → EXPLIQUE + propose alternatives (PAS de code)
"""

# --- Fonctions de génération de PDF ---

def detect_pdf_request(prompt: str) -> bool:
    """
    Détecte si l'utilisateur demande un PDF de la conversation.
    """
    pdf_keywords = [
        r'\bpdf\b',
        r'\brapport\b',
        r'\bdocument\b',
        r'\bexport\w*\b',
        r'\bt[ée]l[ée]charg\w*\b',
        r'\bg[ée]n[ée]r\w*\s+(un\s+)?rapport\b',
        r'\bcr[ée]\w*\s+(un\s+)?pdf\b',
        r'\bfaire\s+un\s+rapport\b',
        r'\bsauvegarder\b',
        r'\benregistrer\b'
    ]
    
    prompt_lower = prompt.lower()
    return any(re.search(pattern, prompt_lower, re.IGNORECASE) for pattern in pdf_keywords)


def analyze_conversation_for_synthesis(messages: list, model) -> dict:
    """
    Utilise Gemini pour créer une synthèse narrative de la conversation.
    Retourne un dictionnaire avec: introduction, analyse_thematique, insights, recommandations
    """
    # Préparer le contexte de la conversation
    conversation_text = "\n\n".join([
        f"{'Utilisateur' if msg['role'] == 'user' else 'Assistant'}: {msg.get('content', '')[:500]}"
        for msg in messages if msg.get('content')
    ])
    
    analysis_prompt = f"""Tu es un analyste senior qui rédige un rapport de synthèse professionnel.

CONVERSATION ANALYSÉE:
{conversation_text}

Ta mission: Créer un rapport narratif et fluide, COMME UN HUMAIN L'ÉCRIRAIT.

GÉNÈRE 4 SECTIONS (sépare-les par "---SECTION---"):

1. **INTRODUCTION** (2-3 phrases)
   - Contexte de l'analyse
   - Période/scope concerné
   - Objectifs de la consultation
   - Ton: Professionnel mais naturel

2. **ANALYSE THÉMATIQUE** (1-2 paragraphes)
   - Regroupe les sujets abordés par thèmes
   - Identifie les préoccupations principales
   - Mentionne les données clés sans format "Question/Réponse"
   - Ton: Analytique et synthétique

3. **OBSERVATIONS ET INSIGHTS** (1-2 paragraphes)
   - Points saillants découverts
   - Tendances observées
   - Corrélations ou patterns identifiés
   - Ton: Objectif et factuel

4. **RECOMMANDATIONS STRATÉGIQUES** (3-5 points numérotés)
   - Actions concrètes et priorisées
   - Basées sur les données réelles discutées
   - Chiffrées quand possible
   - Ton: Directif et actionnable

EXEMPLE DE STRUCTURE:

L'analyse des données de gestion des événements révèle plusieurs axes d'attention prioritaires. L'utilisateur a consulté les informations relatives aux incidents critiques du dernier trimestre, ainsi que les mesures correctives associées.

---SECTION---

L'examen des événements montre une concentration des incidents de niveau 3, représentant 45% des cas traités. Les domaines principaux concernés incluent la sécurité opérationnelle et la gestion des équipements. Une attention particulière a été portée aux délais de résolution, avec une moyenne constatée de 72 heures pour les incidents critiques.

---SECTION---

Trois observations majeures émergent de cette analyse. Premièrement, une hausse de 28% des incidents est constatée sur les trois derniers mois. Deuxièmement, 60% des mesures correctives restent au statut "en cours" au-delà du délai prévu. Troisièmement, les événements récurrents sur les mêmes équipements suggèrent une maintenance insuffisante.

---SECTION---

1. **Renforcer la surveillance proactive**: Mettre en place un système d'alerte automatique pour les équipements présentant plus de 2 incidents par mois.
2. **Accélérer la résolution des mesures correctives**: Assigner des responsables clairs pour les 15 actions en attente depuis plus de 30 jours.
3. **Planifier une maintenance préventive renforcée**: Cibler prioritairement les 5 équipements ayant généré 40% des incidents du trimestre.

MAINTENANT, GÉNÈRE TON RAPPORT BASÉ SUR LA CONVERSATION RÉELLE:"""
    
    try:
        response = model.generate_content(analysis_prompt)
        content = response.text.strip()
        
        # Séparer les sections
        sections = content.split("---SECTION---")
        
        if len(sections) >= 4:
            return {
                'introduction': sections[0].strip(),
                'analyse_thematique': sections[1].strip(),
                'insights': sections[2].strip(),
                'recommandations': sections[3].strip()
            }
        else:
            # Fallback si le format n'est pas respecté
            return {
                'introduction': content[:500] if len(content) > 500 else content,
                'analyse_thematique': content[500:1000] if len(content) > 1000 else content[500:],
                'insights': "L'analyse des données révèle plusieurs points d'attention nécessitant un suivi approfondi.",
                'recommandations': "1. **Poursuivre la surveillance**: Continuer à monitorer les indicateurs clés.\n2. **Optimiser les processus**: Identifier les axes d'amélioration prioritaires."
            }
    except Exception as e:
        return {
            'introduction': "Cette analyse porte sur la consultation des données de gestion d'événements et de risques effectuée via l'assistant IA.",
            'analyse_thematique': "Les thématiques principales abordées concernent l'identification des incidents critiques, l'évaluation des risques opérationnels et le suivi des mesures correctives.",
            'insights': "Les données consultées mettent en évidence plusieurs axes d'amélioration dans la gestion proactive des risques et la rapidité de mise en œuvre des actions correctives.",
            'recommandations': "1. **Renforcer la surveillance**: Mettre en place des indicateurs de suivi régulier.\n2. **Améliorer la réactivité**: Réduire les délais de traitement des incidents critiques.\n3. **Optimiser la documentation**: Assurer une traçabilité complète de toutes les actions."
        }


def generate_professional_pdf(messages: list, model) -> BytesIO:
    """
    Génère un rapport PDF professionnel de la conversation avec recommandations.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Styles personnalisés
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1e3a8a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2563eb'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#1e40af'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        spaceAfter=10,
        alignment=TA_JUSTIFY,
        fontName='Helvetica'
    )
    
    user_style = ParagraphStyle(
        'UserMessage',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#059669'),
        spaceAfter=8,
        fontName='Helvetica-Bold',
        leftIndent=20
    )
    
    assistant_style = ParagraphStyle(
        'AssistantMessage',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#4b5563'),
        spaceAfter=12,
        alignment=TA_JUSTIFY,
        leftIndent=20,
        fontName='Helvetica'
    )
    
    recommendation_style = ParagraphStyle(
        'Recommendation',
        parent=styles['BodyText'],
        fontSize=10,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=10,
        leftIndent=20,
        fontName='Helvetica'
    )
    
    # Contenu du PDF
    story = []
    
    # En-tête avec ligne décorative
    story.append(Paragraph("🛡️ RAPPORT D'ANALYSE", title_style))
    story.append(Paragraph("Gestion d'Événements & Risques", subheading_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Informations du rapport
    current_date = datetime.now().strftime("%d/%m/%Y à %H:%M")
    info_data = [
        ['Date du rapport:', current_date],
        ['Nombre de messages:', str(len(messages))],
        ['Générateur:', 'Assistant IA Gemini'],
        ['Type:', 'Analyse conversationnelle']
    ]
    
    info_table = Table(info_data, colWidths=[2.5*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e0e7ff')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e3a8a')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.4 * inch))
    
    # Générer la synthèse narrative avec l'IA
    with st.spinner("📝 Génération de la synthèse narrative..."):
        synthesis = analyze_conversation_for_synthesis(messages, model)
    
    # Section 1: INTRODUCTION / CONTEXTE
    story.append(Paragraph("📊 CONTEXTE DE L'ANALYSE", heading_style))
    intro_text = synthesis.get('introduction', 'Introduction non disponible')
    story.append(Paragraph(intro_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Section 2: ANALYSE THÉMATIQUE
    story.append(Paragraph("� ANALYSE THÉMATIQUE", heading_style))
    analyse_text = synthesis.get('analyse_thematique', 'Analyse non disponible')
    story.append(Paragraph(analyse_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Section 3: VISUALISATIONS ET DONNÉES CLÉS
    # Extraire les graphiques de la conversation
    charts = [msg.get('chart') for msg in messages if 'chart' in msg]
    
    if charts:
        story.append(Paragraph("📈 VISUALISATIONS DES DONNÉES", heading_style))
        story.append(Paragraph("Les graphiques ci-dessous illustrent les principales tendances identifiées lors de l'analyse:", body_style))
        story.append(Spacer(1, 0.2 * inch))
        
        for idx, chart in enumerate(charts, 1):
            try:
                # Exporter le graphique Plotly en image
                img_bytes = chart.to_image(format="png", width=600, height=400)
                img_buffer = BytesIO(img_bytes)
                
                story.append(Paragraph(f"<b>Figure {idx}</b>", subheading_style))
                img = Image(img_buffer, width=5.5*inch, height=3.7*inch)
                story.append(img)
                story.append(Spacer(1, 0.25 * inch))
            except Exception as e:
                story.append(Paragraph(f"<i>[Graphique {idx} non disponible]</i>", body_style))
                story.append(Spacer(1, 0.1 * inch))
        
        story.append(Spacer(1, 0.2 * inch))
    
    # Section 4: OBSERVATIONS ET INSIGHTS
    story.append(Paragraph("💡 OBSERVATIONS ET INSIGHTS", heading_style))
    insights_text = synthesis.get('insights', 'Insights non disponibles')
    story.append(Paragraph(insights_text.replace('<', '&lt;').replace('>', '&gt;'), body_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Page break avant recommandations
    story.append(PageBreak())
    
    # Section 5: RECOMMANDATIONS STRATÉGIQUES
    story.append(Paragraph("🎯 RECOMMANDATIONS STRATÉGIQUES", heading_style))
    story.append(Spacer(1, 0.15 * inch))
    
    story.append(Paragraph("""Sur la base de l'analyse effectuée, voici les axes d'action prioritaires 
    pour optimiser la gestion des événements et renforcer la maîtrise des risques:""", body_style))
    story.append(Spacer(1, 0.2 * inch))
    
    # Ajouter les recommandations
    recommendations_text = synthesis.get('recommandations', 'Recommandations non disponibles')
    story.append(Paragraph(recommendations_text.replace('<', '&lt;').replace('>', '&gt;'), recommendation_style))
    story.append(Spacer(1, 0.3 * inch))
    
    # Footer / Conclusion
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("📝 CONCLUSION", heading_style))
    conclusion_text = """Ce rapport synthétise les échanges et fournit des recommandations actionnables 
    pour optimiser la gestion des événements et des risques au sein de votre organisation. 
    Il est recommandé de mettre en œuvre ces suggestions de manière progressive et de mesurer leur impact."""
    story.append(Paragraph(conclusion_text, body_style))
    
    story.append(Spacer(1, 0.4 * inch))
    story.append(Paragraph(f"<i>Rapport généré automatiquement le {current_date}</i>", 
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, 
                                       textColor=colors.grey, alignment=TA_CENTER)))
    
    # Construction du PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


# --- Interface Streamlit ---

# En-tête
st.title("🛡️ Assistant Gestion d'Événements & Risques")
st.markdown(f"*Propulsé par {model_name}*")

# Barre latérale avec informations
with st.sidebar:
    st.header("� Bienvenue !")
    st.markdown("""
    Pose tes questions sur les événements, risques et mesures correctives.
    
    **Exemples:**
    - "Événements récents ?"
    - "Risques critiques ?"
    - "Graphique des événements par type"
    - "Visualise la répartition des risques"
    - "Génère un rapport PDF" 📄
    """)
    
    st.divider()
    
    # Bouton pour générer un PDF
    st.subheader("📄 Rapport de Synthèse")
    st.markdown("Génère un rapport narratif professionnel")
    st.caption("Format analytique comme un rapport humain")
    
    message_count = len([m for m in st.session_state.get('messages', []) if m['role'] == 'user'])
    
    if message_count < 2:
        st.info("💡 Pose au moins 2 questions avant de générer un rapport")
        st.button("📄 Générer le rapport", disabled=True, use_container_width=True)
    else:
        if st.button("📄 Générer le rapport", use_container_width=True, type="primary"):
            # Simuler une demande de PDF
            st.session_state.pdf_requested = True
            st.rerun()
    
    st.divider()
    
    if st.button("🔄 Réinitialiser", use_container_width=True):
        st.session_state.messages = []
        st.session_state.conversation_history = []  # Nettoyer aussi la mémoire
        st.rerun()

# Gestion de la demande de PDF depuis le bouton sidebar
if st.session_state.get('pdf_requested', False):
    st.session_state.pdf_requested = False
    
    with st.chat_message("assistant"):
        st.markdown("### 📄 Génération du rapport PDF en cours...")
        
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

# Initialisation de l'historique des messages et de la conversation
if "messages" not in st.session_state:
    st.session_state.messages = []
    welcome_message = """### 👋 Assistant Événements

Je réponds rapidement à vos questions sur:
- 📋 Événements & incidents
- ⚠️ Risques  
- ✅ Mesures correctives
- 👥 Personnes impliquées

**Exemples:**
- "Événements récents"
- "Risques critiques"
- "Graphique des événements par mois"
- "Visualise la répartition des types"

**Pose ta question !** 🚀
"""
    st.session_state.messages.append({
        "role": "assistant",
        "content": welcome_message
    })

# Initialisation de l'historique de conversation (pour mémoire SQL)
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Affichage de l'historique des messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # Afficher le contenu texte d'abord
        if "content" in message:
            st.markdown(message["content"])
        
        # Si le message contient un graphique (figure plotly sauvegardée)
        if "chart" in message:
            st.plotly_chart(message["chart"], use_container_width=True)

# Zone de saisie utilisateur
if prompt := st.chat_input("Posez votre question sur les événements, risques ou mesures..."):
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

## ⚠️ ANALYSE DES DONNÉES AVANT DE RÉPONDRE:
1. Vérifie si le contexte contient des données réelles ou juste "Aucune donnée"
2. Si pas de données → NE génère PAS de graphique, explique pourquoi + propose alternatives
3. Si données présentes → Tu peux générer un graphique SI demandé

## Question utilisateur (PRIORITÉ ABSOLUE):
{prompt}

## FORMAT RÉPONSE:

### SI DONNÉES PRÉSENTES:
**STRUCTURE:**
1. Résumé en 1 ligne (chiffre clé)
2. Tableau compact (max 5 colonnes essentielles)
3. Insight/observation importante (1 phrase avec 💡)

**EXEMPLE:**
```
**15 événements trouvés** (10 premiers affichés)

| ID | Description | Date | Type |
|---|---|---|---|
| 125 | Panne ligne A | 28/10 | Incident |
| 124 | Chute escalier | 27/10 | Accident |

💡 40% sont de type "Incident", majoritairement résolus
```

### SI PAS DE DONNÉES:
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

**RÈGLES:**
- Max 10 lignes de tableau
- Dates format court: JJ/MM
- Pas de phrases longues
- Mets en gras les chiffres importants
- Si >10 résultats: indique le total mais affiche que 10
- **NE génère du code QUE si données valides ET demande de graphique**
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
