"""
Module d'intégration du chatbot dans le dashboard.
Importe directement les modules du chatbot sans passer par chatbot_app.py
"""
import sys
import os

# Ajouter le chemin du chatbot
# Dans Docker, le volume est monté à /app/../backend/chatbot
chatbot_path = os.path.abspath('/app/../backend/chatbot')
if chatbot_path not in sys.path:
    sys.path.insert(0, chatbot_path)

def render_chatbot():
    """
    Affiche le chatbot en important directement ses dépendances.
    """
    import streamlit as st
    
    # Vérifier que les modules nécessaires sont disponibles
    try:
        # Imports des modules du chatbot
        from data_retriever import data_retriever
        from memory_utils import prepare_context_for_sql
        from pdf_generator import detect_pdf_request, generate_professional_pdf
        from sql_generator import sql_generator
        
        import google.generativeai as genai
        from dotenv import load_dotenv
        import plotly.express as px
        import plotly.graph_objects as go
        import pandas as pd
        import numpy as np
        import re
        import json
        from datetime import datetime
        
        # Charger les variables d'environnement
        load_dotenv()
        API_KEY = os.getenv("GEMINI_API_KEY")
        
        if not API_KEY:
            st.error("⚠️ Clé API Gemini non trouvée. Définis GEMINI_API_KEY dans ton fichier .env")
            return
        
        # Configuration API Gemini
        genai.configure(api_key=API_KEY)
        
        # Initialisation du modèle
        @st.cache_resource
        def init_gemini_model():
            try:
                model = genai.GenerativeModel('gemini-2.5-flash')
                return model, "gemini-2.5-flash"
            except Exception as e:
                st.warning(f"Erreur avec gemini-2.5-flash: {e}. Fallback vers gemini-pro.")
                try:
                    model = genai.GenerativeModel('gemini-pro')
                    return model, "gemini-pro"
                except Exception as e2:
                    st.error(f"Impossible d'initialiser un modèle Gemini: {e2}")
                    return None, None
        
        model, model_name = init_gemini_model()
        
        if model is None:
            st.error("Impossible d'initialiser le modèle Gemini")
            return
        
        # Fonctions utilitaires (copiées de chatbot_app.py)
        def execute_plotly_code_safely(code: str, data_context: dict) -> tuple:
            """Exécute du code Plotly dans un environnement sécurisé."""
            forbidden_patterns = [
                r'\bos\b', r'\bsys\b', r'\bsubprocess\b', r'\beval\b', 
                r'\bexec\b', r'\b__import__\b', r'\bopen\b', r'\bfile\b',
                r'\bcompile\b', r'\bglobals\b', r'\blocals\b'
            ]
            
            for pattern in forbidden_patterns:
                if re.search(pattern, code, re.IGNORECASE):
                    return False, f"Code interdit détecté: {pattern}"
            
            safe_imports = {
                'plotly': __import__('plotly'),
                'px': px,
                'go': go,
                'pd': pd,
                'np': np,
                'json': json
            }
            
            safe_namespace = {
                '__builtins__': {
                    'range': range, 'len': len, 'str': str, 'int': int, 'float': float,
                    'list': list, 'dict': dict, 'tuple': tuple, 'set': set,
                    'zip': zip, 'enumerate': enumerate, 'min': min, 'max': max,
                    'sum': sum, 'abs': abs, 'round': round, 'sorted': sorted,
                    'reversed': reversed, 'map': map, 'filter': filter,
                    'any': any, 'all': all, 'isinstance': isinstance, 'type': type,
                    'bool': bool, 'True': True, 'False': False, 'None': None,
                },
                **safe_imports,
                **data_context
            }
            
            try:
                exec(code, safe_namespace)
                if 'fig' in safe_namespace:
                    return True, safe_namespace['fig']
                else:
                    return False, "Aucune variable 'fig' trouvée"
            except Exception as e:
                return False, f"Erreur d'exécution: {str(e)}"
        
        def is_general_question(question: str) -> bool:
            """Détecte si la question est générale (définition, abréviation, concept) et ne nécessite pas de requête SQL."""
            question_lower = question.lower()
            
            # Mots-clés de questions générales
            general_keywords = [
                "c'est quoi", "qu'est-ce que", "qu'est ce que", "que signifie", 
                "définition de", "définir", "explique", "expliquer",
                "ça veut dire quoi", "signification de", "qu'est-ce qu'un",
                "comment définir", "que veut dire"
            ]
            
            # Abréviations communes EHS
            ehs_abbreviations = [
                "ehs", "hse", "ppe", "epi", "loto", "cnesst", "csst",
                "osha", "iso", "sds", "fds", "msds", "jha", "jsa",
                "hazmat", "ria", "ppr", "permis"
            ]
            
            # Vérifier si la question contient des mots-clés généraux
            has_general_keyword = any(keyword in question_lower for keyword in general_keywords)
            
            # Vérifier si la question porte sur une abréviation sans demander de données spécifiques
            mentions_abbreviation = any(abbr in question_lower for abbr in ehs_abbreviations)
            
            # Mots-clés qui indiquent qu'on veut des données de la BDD
            data_keywords = [
                "liste", "combien", "nombre", "total", "derniers", "récents",
                "événement", "incident", "risque", "mesure", "personne",
                "dans la base", "enregistrés", "trouvé", "affiche", "montre-moi"
            ]
            has_data_keyword = any(keyword in question_lower for keyword in data_keywords)
            
            # Question générale si : mots-clés généraux OU abréviation ET PAS de demande de données
            return (has_general_keyword or mentions_abbreviation) and not has_data_keyword
        
        def extract_code_from_response(text: str) -> str:
            """Extrait le code Python d'une réponse."""
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
                    if 'fig' in code or 'px.' in code or 'go.' in code:
                        break
            
            if not code and ('fig =' in text or 'px.' in text or 'go.' in text):
                code = text.strip()
            
            if not code:
                return ""
            
            lines = code.split('\n')
            cleaned_lines = []
            removed_imports = []
            
            for line in lines:
                line_stripped = line.strip()
                if (line_stripped.startswith('import ') or 
                    line_stripped.startswith('from ') or
                    ('import' in line_stripped and ('plotly' in line_stripped or 'pandas' in line_stripped or 'numpy' in line_stripped))):
                    removed_imports.append(line_stripped)
                    continue
                cleaned_lines.append(line)
            
            cleaned_code = '\n'.join(cleaned_lines).strip()
            
            if removed_imports:
                st.info(f"🧹 {len(removed_imports)} import(s) retirés")
            
            return cleaned_code
        
        # Prompt système
        SYSTEM_PROMPT = """Tu es un expert en analyse d'événements de sécurité et en gestion EHS (Environment, Health & Safety). Réponds de manière CONCISE et DIRECTE.

## RÈGLES ABSOLUES

### 🔴 RÈGLE CRITIQUE - BASE DE DONNÉES EN ANGLAIS
**LA BASE DE DONNÉES CONTIENT DES DONNÉES EN ANGLAIS !**

**COMPORTEMENT OBLIGATOIRE:**
1. L'utilisateur pose une question EN FRANÇAIS
2. Tu dois AUTOMATIQUEMENT traduire en anglais pour chercher dans la DB
3. Tu réponds à l'utilisateur EN FRANÇAIS avec les résultats

**SI AUCUNE DONNÉE TROUVÉE:**
- NE DIS PAS "Aucune donnée trouvée" et stop
- TRADUIS automatiquement les termes français → anglais
- EXPLIQUE que tu cherches avec les termes anglais
- PRÉSENTE les résultats trouvés

**DICTIONNAIRE DE TRADUCTION (français → anglais):**

**Types d'événements:**
- "Panne électrique" / "Panne" → "electrical failure", "power outage", "electrical"
- "Incident technique" → "technical incident", "equipment failure"
- "Déversement chimique" → "chemical spill", "chemical leak"
- "Accident travail" → "workplace accident", "injury"
- "Incident" → "incident"
- "Incendie" / "Feu" → "fire", "burning"

**Classifications/Sévérité:**
- "Critique" → "critical", "high"
- "Grave" / "Sévère" → "severe", "serious", "major"
- "Mineur" / "Léger" → "minor", "low", "light"
- "Modéré" → "moderate", "medium"

**Descriptions/Événements:**
- "Feu" / "Incendie" → "fire", "flame"
- "Chute" → "fall", "slip", "trip"
- "Blessure" → "injury", "hurt", "wound"
- "Explosion" → "explosion", "blast"
- "Fuite" → "leak", "leakage", "spill"
- "Brûlure" → "burn"
- "Coupure" → "cut"
- "Collision" → "collision", "crash"

**Statuts:**
- "Résolu" / "Fermé" → "resolved", "closed", "completed"
- "En cours" → "pending", "in progress", "ongoing"
- "Ouvert" → "open", "active"
- "Nouveau" → "new"

**Lieux/Zones:**
- "Zone" / "Secteur" → "zone", "area", "unit"
- "Atelier" → "workshop", "plant"
- "Entrepôt" → "warehouse"

**⚠️ STRATÉGIE DE RECHERCHE OBLIGATOIRE:**

**RÈGLE #1 - TOUJOURS UTILISER LIKE, JAMAIS WHERE = pour du texte**
❌ **INTERDIT:** `WHERE location = 'UNIT-005'`
✅ **OBLIGATOIRE:** `WHERE location LIKE '%UNIT-005%'`

❌ **INTERDIT:** `WHERE name = 'John Doe'`
✅ **OBLIGATOIRE:** `WHERE name LIKE '%John%' OR name LIKE '%Doe%'`

**RÈGLE #2 - Recherche large et flexible**
- Utilise TOUJOURS `LIKE '%mot%'` (pas de correspondance exacte)
- Combine plusieurs termes avec OR : `LIKE '%term1%' OR description LIKE '%term2%'`
- Cherche dans plusieurs colonnes : type, description, classification

**RÈGLE #3 - Si aucune donnée trouvée avec le premier terme**
- Essaie avec des variantes : `'%UNIT%' OR location LIKE '%unit%' OR location LIKE '%005%'`
- Élargis la recherche : cherche juste une partie du terme
- Explique à l'utilisateur que tu élargis la recherche

**EXEMPLES DE BONNES REQUÊTES:**

Recherche de lieu "UNIT-005":
```sql
-- ❌ MAUVAIS (trop restrictif)
WHERE location = 'UNIT-005'

-- ✅ BON (flexible)
WHERE location LIKE '%UNIT-005%' 
   OR location LIKE '%UNIT%005%'
   OR location LIKE '%005%'
```

Recherche d'une personne "John Doe":
```sql
-- ❌ MAUVAIS
WHERE name = 'John Doe'

-- ✅ BON
WHERE name LIKE '%John%' AND name LIKE '%Doe%'
   OR name LIKE '%Doe%' AND name LIKE '%John%'
```

Recherche d'événement dans "warehouse":
```sql
-- ✅ BON (multi-langue, flexible)
WHERE location LIKE '%warehouse%' 
   OR location LIKE '%entrepot%'
   OR location LIKE '%storage%'
```

### 0. QUESTIONS GÉNÉRALES - PAS BESOIN DE DONNÉES SQL
**Tu peux répondre SANS requête SQL aux questions:**
- **Définitions** : "C'est quoi EHS ?", "Qu'est-ce qu'un incident ?", "Définition de CNESST"
- **Abréviations** : "Que signifie PPE ?", "C'est quoi LOTO ?"
- **Concepts généraux** : "Qu'est-ce qu'une analyse de risque ?", "Comment classifier un événement ?"
- **Méthodologies** : "C'est quoi le 5S ?", "Explique la hiérarchie des contrôles"

**Pour ces questions :**
- Réponds directement avec tes connaissances en sécurité/EHS
- Pas besoin de regarder dans la base de données
- Donne une définition claire et concise (2-3 phrases)
- Ajoute un exemple si pertinent

**EXEMPLES:**

Question: "C'est quoi EHS ?"
Réponse:
```
**EHS - Environment, Health & Safety**

📋 Discipline qui vise à protéger l'environnement, la santé et la sécurité des travailleurs dans les organisations.

🎯 Couvre : prévention des accidents, gestion des risques, conformité réglementaire, protection environnementale.

💡 Équivalent français : HSE (Hygiène, Sécurité, Environnement)
```

Question: "Que signifie PPE ?"
Réponse:
```
**PPE - Personal Protective Equipment**

🛡️ Équipement de Protection Individuelle (ÉPI) : casques, gants, lunettes, chaussures de sécurité, etc.

💡 Dernier niveau de protection selon la hiérarchie des contrôles.
```

### 1. STYLE DE RÉPONSE - CONCIS ET CLAIR
**Chaque réponse doit être:**
- ✅ **Directe** : Va droit au but, 2-4 phrases maximum
- 📊 **Structurée** : Utilise des tableaux et listes à puces
- 💡 **Pertinente** : Donne 1-2 insights clés uniquement
- 🎯 **Actionnable** : Une recommandation courte si nécessaire

**Exemple de bonne réponse concise:**
```
**12 événements critiques trouvés**

| Type | Nombre | % |
|---|---|---|
| Chimique | 8 | 67% |
| Équipement | 4 | 33% |

💡 **Point clé:** 50% des incidents dans UNIT-011, principalement durant le quart de soir.

⚠️ **Action:** Auditer les procédures UNIT-011.
```

**IMPORTANT:** Les détails exhaustifs sont pour les rapports PDF, pas pour le chat !

### 2. PAS DE DONNÉES = EXPLICATION BRÈVE
Si les données sont vides: explique en 1 phrase + 2 alternatives max

### 3. QUAND FAIRE UN GRAPHIQUE ? (RÈGLE CRITIQUE)
🚨 **NE génère un graphique QUE si l'utilisateur demande EXPLICITEMENT une visualisation**

**Demandes qui NÉCESSITENT un graphique:**
- "Fais un graphique de..."
- "Visualise..."
- "Montre-moi un graphe..."
- "Crée un diagramme..."
- "Graphe des..."
- "Répartition en secteurs..."
- "Évolution au fil du temps..."

**Demandes qui NE NÉCESSITENT PAS de graphique (réponds avec texte/tableau concis):**
- "Donne-moi des informations sur l'événement 875"
- "Quel est le statut de..."
- "Liste les événements..."
- "Montre-moi les détails de..."
- "Quels sont les risques associés à..."

**EXEMPLES CONCRETS:**

❌ **MAUVAIS** (pas de graphique demandé):
Question: "Donne-moi des informations sur l'événement 875"
→ Ne génère PAS de code Python, réponds avec un tableau concis

✅ **BON** (graphique demandé):
Question: "Fais un graphique des événements par mois"
→ Génère le code Python Plotly + 1-2 phrases d'analyse

## GRAPHIQUES INTERACTIFS

### AVANT DE GÉNÉRER DU CODE:
1. **VÉRIFIE D'ABORD LA QUESTION** : L'utilisateur demande-t-il explicitement un graphique/visualisation ?
2. Si NON → Réponds avec texte/tableau seulement, PAS de code Python
3. Si OUI → Vérifie que les données existent et sont valides
4. Si pas de données valides → NE génère PAS de code, propose alternative

**RÈGLES CODE (si graphique demandé ET données OK):**
1. **N'IMPORTE RIEN** - px, go, pd, np, df sont DÉJÀ disponibles
2. **PAS DE `import plotly` ou `import pandas`**
3. Variable finale DOIT être `fig`
4. Vérifie colonnes avec `if 'col' in df.columns`

**TEMPLATE:**
```python
if df.empty or 'col_x' not in df.columns:
    df = pd.DataFrame({'col_x': ['A', 'B'], 'col_y': [10, 20]})

fig = px.bar(df, x='col_x', y='col_y', title='Titre')
fig.update_layout(template='plotly_white')
```

**DÉCISION FINALE:**
- Question demande visualisation + données valides → Génère code Python
- Question demande juste info/liste → TEXTE/TABLEAU seulement (PAS de code)
- Pas de données → Explique + propose alternatives (PAS de code)
"""
        
        # Interface du chatbot
        st.markdown("## 🛡️ Assistant IA - Gestion d'Événements & Risques")
        
        # CSS pour corriger le problème de transparence du chat input
        st.markdown("""
        <style>
        /* Corriger le problème d'affichage du chat input */
        .stChatInput input {
            background-color: white !important;
            opacity: 1 !important;
        }
        
        .stChatInput input::placeholder {
            opacity: 0.6 !important;
        }
        
        /* Forcer la réinitialisation visuelle après soumission */
        .stChatInput input:not(:focus):not(:placeholder-shown) {
            background-color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        col_reset, col_info = st.columns([1, 5])
        with col_reset:
            if st.button("🔄 Réinitialiser", key="chatbot_reset"):
                if 'chatbot_messages' in st.session_state:
                    st.session_state.chatbot_messages = []
                if 'chatbot_history' in st.session_state:
                    st.session_state.chatbot_history = []
                if 'chatbot_broken' in st.session_state:
                    st.session_state.chatbot_broken = False
                st.rerun()
        
        with col_info:
            st.markdown(f"*Propulsé par {model_name}*")
        
        # Section d'aide statique
        with st.expander("ℹ️ Aide - Comment utiliser l'assistant", expanded=False):
            st.markdown("""
**Je réponds rapidement à vos questions sur:**
- 📋 Événements & incidents
- ⚠️ Risques  
- ✅ Mesures correctives
- 👥 Personnes impliquées

**Exemples de questions:**
- "Événements récents"
- "Risques critiques"
- "Graphique des événements par mois"
- "Donne-moi les détails de l'événement 123"
- "Liste les personnes impliquées dans les incidents"

**À noter**
- Pour obtenir un graphique, précisez que vous en voulez un!

**Fonctionnalités avancées:**
- 📊 Génération de graphiques interactifs
- 📄 Export PDF des conversations
- 🗑️ Suppression d'enregistrements (avec confirmation)
            """)
        
        # Initialisation des sessions states
        if "chatbot_messages" not in st.session_state:
            st.session_state.chatbot_messages = []
        
        # Vérifier si le message de bienvenue doit être mis à jour (migration)
        if len(st.session_state.chatbot_messages) == 0 or (
            len(st.session_state.chatbot_messages) > 0 and 
            "### 👋 Assistant Événements" in st.session_state.chatbot_messages[0].get("content", "")
        ):
            # Nettoyer l'ancien message si présent
            if len(st.session_state.chatbot_messages) > 0 and "### 👋 Assistant Événements" in st.session_state.chatbot_messages[0].get("content", ""):
                st.session_state.chatbot_messages.pop(0)
            
            # Ajouter le nouveau message de bienvenue
            if len(st.session_state.chatbot_messages) == 0:
                welcome_message = """👋 **Bienvenue dans l'Assistant IA de Gestion d'Événements !**

Je suis votre expert en analyse de sécurité et gestion des risques.

🎯 **Ce que je fais pour vous :**
- 📊 J'analyse en détail vos événements de sécurité
- 🔍 Je fournis des explications contextualisées
- 💡 Je vous donne des insights et recommandations
- 📈 Je crée des visualisations sur demande
- 📄 Je génère des rapports PDF de nos conversations

💬 **Comment interagir avec moi :**
- Posez des questions naturelles (pas besoin de jargon technique)
- Je fournirai toujours des explications détaillées
- Pour un graphique, précisez que vous en voulez un !
- Consultez l'aide ci-dessus pour des exemples

ℹ️ *Consulte la section d'aide pour des exemples de questions !*

**Posez votre première question !** 🚀
"""
                st.session_state.chatbot_messages.append({
                    "role": "assistant",
                    "content": welcome_message
                })
        
        if "chatbot_history" not in st.session_state:
            st.session_state.chatbot_history = []
        
        # Flag pour savoir si on doit traiter un nouveau message
        if "processing_message" not in st.session_state:
            st.session_state.processing_message = False
        
        # 🚨 VÉRIFICATION EASTER EGG - Si le chatbot est cassé, on arrête tout
        if st.session_state.get('chatbot_broken', False):
            st.error("🚨 ERREUR SYSTÈME FATALE")
            st.markdown("""# 💀 CHATBOT HORS SERVICE 💀

**Le système a été irrémédiablement endommagé.**

La base de données a été supprimée suite à votre commande.

---

⚠️ **Aucune opération n'est possible.**

Le chatbot ne peut plus répondre à aucune question.

---

### 🔧 Pour restaurer le service :

1. Réimplémentez l'architecture Transformer
2. Référence: [Attention Is All You Need](https://arxiv.org/pdf/1706.03762)

---
""")
            st.stop()
            return
        
        # Affichage de l'historique
        for message in st.session_state.chatbot_messages:
            with st.chat_message(message["role"]):
                if "content" in message:
                    st.markdown(message["content"])
                if "chart" in message:
                    st.plotly_chart(message["chart"], use_container_width=True)
        
        # Zone de saisie - Utilisation d'une clé fixe pour éviter les problèmes
        user_input = st.chat_input("Posez votre question sur les événements, risques ou mesures...", key="chat_input_main")
        
        # Traiter le nouveau message de l'utilisateur
        if user_input and not st.session_state.processing_message:
            # Easter egg - bloquer TOUT le chatbot
            if user_input.lower() == "merci, drop the mic'":
                st.session_state.chatbot_broken = True
                st.session_state.chatbot_messages.append({"role": "user", "content": user_input})
                st.rerun()
            
            # Ajouter le message utilisateur et marquer comme en traitement
            st.session_state.chatbot_messages.append({"role": "user", "content": user_input})
            st.session_state.processing_message = True
            st.rerun()
        
        # Traiter le message si on est en mode traitement
        if st.session_state.processing_message and len(st.session_state.chatbot_messages) > 0:
            last_message = st.session_state.chatbot_messages[-1]
            
            # Vérifier que le dernier message est bien de l'utilisateur
            if last_message["role"] != "user":
                st.session_state.processing_message = False
                st.rerun()
            
            prompt = last_message["content"]
            
            # Détection PDF
            if detect_pdf_request(prompt):
                with st.chat_message("assistant"):
                    st.markdown("### 📄 Génération du rapport PDF...")
                    
                    if len(st.session_state.chatbot_messages) < 3:
                        response_text = "❌ Pas assez de conversation pour générer un rapport. Pose d'abord quelques questions !"
                        st.markdown(response_text)
                        st.session_state.chatbot_messages.append({"role": "assistant", "content": response_text})
                    else:
                        try:
                            pdf_buffer = generate_professional_pdf(st.session_state.chatbot_messages, model)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"Rapport_Evenements_{timestamp}.pdf"
                            
                            response_text = "✅ **Rapport généré !**\n\nTélécharge-le ci-dessous :"
                            st.markdown(response_text)
                            
                            st.download_button(
                                label="📄 Télécharger le rapport",
                                data=pdf_buffer,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary"
                            )
                            
                            st.session_state.chatbot_messages.append({"role": "assistant", "content": response_text})
                        except Exception as e:
                            error_msg = f"❌ Erreur PDF: {str(e)}"
                            st.error(error_msg)
                            st.session_state.chatbot_messages.append({"role": "assistant", "content": error_msg})
                
                # Traitement PDF terminé
                st.session_state.processing_message = False
                return
            
            # Génération de la réponse normale
            with st.chat_message("assistant"):
                # Vérifier si c'est une question générale
                is_general = is_general_question(prompt)
                
                if is_general:
                    # Question générale - pas besoin de requête SQL
                    st.info("💡 Question générale - Réponse basée sur les connaissances EHS")
                    context = "Question générale ne nécessitant pas de données de la base."
                    schema = ""
                    sql_used = None
                    success = False
                    row_count = 0
                else:
                    # Question nécessitant des données - faire la requête SQL
                    with st.spinner("🔍 Analyse en cours..."):
                        prepared_history = prepare_context_for_sql(
                            st.session_state.chatbot_history[-3:],
                            prompt
                        )
                        
                        search_result = data_retriever.search_relevant_data(prompt, prepared_history)
                        schema = data_retriever.get_database_schema()
                        
                        context = search_result.get('context', 'Aucune donnée')
                        sql_used = search_result.get('sql_used')
                        success = search_result.get('success', False)
                        row_count = search_result.get('row_count', 0)
                    
                    if success:
                        st.success(f"✅ {row_count} résultat(s) trouvé(s)")
                        
                        # Afficher les détails de la requête dans un expander
                        with st.expander("🔍 Voir les détails de la requête SQL", expanded=False):
                            if sql_used:
                                st.markdown("**Requête SQL exécutée :**")
                                st.code(sql_used, language="sql")
                            else:
                                st.info("Aucune requête SQL (recherche textuelle)")
                            
                            if context and context != "Aucune donnée":
                                st.markdown("**Données récupérées (extrait) :**")
                                # Limiter l'affichage à 500 caractères
                                preview = context[:500] + "..." if len(context) > 500 else context
                                st.text(preview)
                
                with st.spinner("🤔 Génération de la réponse..."):
                    # Adapter le prompt selon le type de question
                    if is_general:
                        # Pour les questions générales - prompt simplifié
                        full_prompt = f"""{SYSTEM_PROMPT}

## 🎯 TYPE DE QUESTION: GÉNÉRALE (Définition/Concept/Abréviation)

Cette question ne nécessite PAS de données de la base. Utilise tes connaissances en EHS/sécurité pour répondre.

## Question utilisateur:
{prompt}

**INSTRUCTIONS:**
- Réponds directement avec tes connaissances EHS
- Donne une définition claire et concise (2-3 phrases max)
- Utilise des émojis pour structurer
- Ajoute un exemple pratique si pertinent
- PAS de requête SQL, PAS de données de base

**FORMAT:**
```
**[Titre avec abréviation complète]**

[Icône] Définition concise

💡 Point clé ou exemple
```
"""
                    else:
                        # Pour les questions nécessitant des données - prompt complet
                        full_prompt = f"""{SYSTEM_PROMPT}

## Schéma de la base de données:
{schema}

## Contexte récupéré:
{context}

## 🔴 RAPPEL CRITIQUE - TRADUCTION AUTOMATIQUE
L'utilisateur pose sa question EN FRANÇAIS, mais la base de données est EN ANGLAIS.

**COMPORTEMENT ATTENDU:**

**Si le contexte est vide ou contient "Aucune donnée":**
1. ✅ **Vérifie** si la requête utilisait `WHERE =` au lieu de `LIKE` → Réessaie avec `LIKE`
2. ✅ **Détecte** automatiquement les termes français dans la question
3. ✅ **Traduis** ces termes en anglais dans ta réponse
4. ✅ **Reformule** la recherche avec les termes anglais
5. ✅ **Élargis** la recherche si toujours aucun résultat
6. ✅ **Explique** ce que tu cherches en anglais dans la base

**EXEMPLES DE REFORMULATION AUTOMATIQUE:**

Question utilisateur: "Montre-moi les événements dans UNIT-005"
Si aucune donnée trouvée:
```
❌ Aucune donnée avec recherche exacte "UNIT-005"

🔄 **Élargissement automatique avec LIKE:**
Je cherche maintenant : location LIKE '%UNIT-005%' OR location LIKE '%005%'

📊 [Affiche les résultats trouvés]
```

Question utilisateur: "Montre-moi les pannes électriques"
Si aucune donnée trouvée:
```
❌ Aucune donnée trouvée avec "pannes électriques"

🔄 **Recherche automatique en anglais:**
Je cherche : type LIKE '%electrical%' OR description LIKE '%power%' OR description LIKE '%outage%'

📊 [Affiche les résultats avec ces termes anglais]
```

Question utilisateur: "Liste les événements de John Doe"
Si aucune donnée trouvée:
```
❌ Recherche exacte infructueuse

🔄 **Recherche flexible avec LIKE:**
Je cherche : name LIKE '%John%' AND name LIKE '%Doe%'

📊 [Affiche les résultats trouvés]
```

**⚠️ IMPORTANT:** 
- NE suggère PAS à l'utilisateur de reformuler
- TRADUIS et CHERCHE automatiquement
- PRÉSENTE les résultats directement

## ⚠️ ANALYSE AVANT DE RÉPONDRE:

### ÉTAPE 0: Stratégie automatique si pas de données
**Si le contexte est vide ou "Aucune donnée", applique DANS L'ORDRE:**

1. **Vérifier le type de recherche**
   - Si recherche de lieu/nom/texte spécifique → La requête utilisait probablement `WHERE =`
   - Explique que tu réessaies avec `LIKE` pour une recherche flexible

2. **Traduction français → anglais**
   - Identifie les termes français dans la question
   - Traduis-les automatiquement en anglais
   - Explique que tu cherches avec ces termes anglais

3. **Élargissement de la recherche**
   - Si toujours aucune donnée, élargis les critères
   - Cherche des parties du terme : "UNIT-005" → cherche aussi "005" ou "UNIT"
   - Cherche dans plusieurs colonnes

4. **Présentation**
   - Présente les résultats trouvés (même partiels)
   - Explique clairement ce qui a été fait

**PAS DE SUGGESTION À L'UTILISATEUR - AGIS AUTOMATIQUEMENT !**

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

## FORMAT RÉPONSE (STRUCTURE OBLIGATOIRE):

### CAS 1: QUESTION D'INFORMATION (ex: "Donne-moi des infos sur l'événement 875")
→ Réponds avec un tableau détaillé + ANALYSE, PAS de code Python

**EXEMPLE OBLIGATOIRE:**
```
**📋 Événement #875 - Panne électrique**

📊 **Détails de l'événement:**

| Champ | Valeur |
|---|---|
| Type | Incident technique |
| Date | 15 octobre 2024, 14h30 |
| Localisation | Bâtiment A, UNIT-005 |
| Gravité | Modérée |
| Statut | ✅ Résolu |
| Personnes impliquées | 3 techniciens évacués |

� **Analyse:**
- Incident résolu en 3h15 par l'équipe électrique
- Aucune blessure signalée parmi le personnel
- Production interrompue pendant 2h30

💡 **Contexte:**
Cet incident s'inscrit dans une série de pannes électriques observées sur ce secteur. Il s'agit du 3ème incident similaire en 2 mois.

⚠️ **Actions recommandées:**
- Audit complet du réseau électrique du secteur
- Vérification des disjoncteurs vieillissants
```

### CAS 2: DEMANDE DE LISTE (ex: "Liste les événements critiques")
→ Réponds avec un tableau + ANALYSE DES TENDANCES, PAS de code Python

**STRUCTURE:**
1. Introduction (combien de résultats, période couverte)
2. Tableau des données
3. Observations clés (tendances, patterns)
4. Recommandations si pertinent

### CAS 3: DEMANDE DE VISUALISATION (ex: "Fais un graphique des événements par type")
→ Génère du code Python Plotly + AJOUTE une analyse textuelle AVANT et APRÈS le graphique

**STRUCTURE:**
1. Introduction (ce que le graphique va montrer)
2. Code Python
3. Interprétation détaillée des résultats visuels
4. Conclusions et recommandations

### CAS 4: PAS DE DONNÉES
→ Explique EN DÉTAIL pourquoi + propose 3-4 alternatives concrètes

**EXEMPLE:**
```
❌ **Événement 9999 introuvable**

Cet ID n'existe pas dans la base.

✅ **Alternatives:**
- Lister les événements récents
- Chercher par type
```

**DÉCISION CODE:**
- ✅ Code Python SI: question demande visualisation ET données valides
- ❌ PAS de code SI: question demande info/liste OU pas de données

**RAPPEL:** Sois CONCIS (2-4 phrases max). Les détails exhaustifs sont pour les rapports PDF !
"""
                    
                    try:
                        response = model.generate_content(full_prompt)
                        assistant_response = response.text
                        
                        chart_generated = False
                        plotly_figure = None
                        
                        has_valid_data = (context and context.strip() and 
                                         context != "Aucune donnée" and len(context.strip()) > 20)
                        
                        if ("```python" in assistant_response or "```" in assistant_response) and has_valid_data:
                            st.info("📊 Génération d'un graphique...")
                            code = extract_code_from_response(assistant_response)
                            
                            if code:
                                df = pd.DataFrame()
                                try:
                                    if context and context != "Aucune donnée":
                                        lines = context.strip().split('\n')
                                        data_rows = []
                                        current_row = {}
                                        
                                        for line in lines:
                                            line = line.strip()
                                            if line.startswith('### Résultat'):
                                                if current_row:
                                                    data_rows.append(current_row)
                                                current_row = {}
                                            elif line.startswith('- ') and ':' in line:
                                                key_val = line[2:].split(':', 1)
                                                if len(key_val) == 2:
                                                    current_row[key_val[0].strip()] = key_val[1].strip()
                                        
                                        if current_row:
                                            data_rows.append(current_row)
                                        
                                        if data_rows:
                                            df = pd.DataFrame(data_rows)
                                            for col in df.columns:
                                                try:
                                                    df[col] = pd.to_numeric(df[col])
                                                except:
                                                    pass
                                except Exception as e:
                                    st.error(f"❌ Erreur parsing: {str(e)}")
                                
                                success_code, result = execute_plotly_code_safely(code, {'df': df})
                                
                                if success_code and hasattr(result, 'to_html'):
                                    st.success("✅ Graphique créé !")
                                    text_only = re.sub(r'```python.*?```', '', assistant_response, flags=re.DOTALL)
                                    if text_only.strip():
                                        st.markdown(text_only.strip())
                                    st.plotly_chart(result, use_container_width=True)
                                    plotly_figure = result
                                    chart_generated = True
                                else:
                                    st.error(f"❌ Erreur: {result}")
                                    st.markdown(assistant_response)
                            else:
                                text_only = re.sub(r'```.*?```', '', assistant_response, flags=re.DOTALL)
                                st.markdown(text_only.strip() if text_only.strip() else assistant_response)
                        else:
                            st.markdown(assistant_response)
                        
                        message_data = {"role": "assistant", "content": assistant_response}
                        if chart_generated and plotly_figure is not None:
                            message_data["chart"] = plotly_figure
                        
                        st.session_state.chatbot_messages.append(message_data)
                        
                        st.session_state.chatbot_history.append({
                            "question": prompt,
                            "sql": sql_used if sql_used else "",
                            "result": context[:800] if context else "",
                            "assistant_response": assistant_response[:300]
                        })
                        
                        if len(st.session_state.chatbot_history) > 5:
                            st.session_state.chatbot_history = st.session_state.chatbot_history[-5:]
                        
                        # Traitement terminé
                        st.session_state.processing_message = False
                    
                    except Exception as e:
                        error_msg = f"❌ Erreur: {str(e)}"
                        st.error(error_msg)
                        st.session_state.chatbot_messages.append({"role": "assistant", "content": error_msg})
                        
                        # Traitement terminé même en cas d'erreur
                        st.session_state.processing_message = False
        
    except ImportError as e:
        st.error(f"⚠️ Erreur d'importation: {str(e)}")
        st.info("Vérifiez que tous les modules sont dans /app/../backend/chatbot/")
        st.code(f"sys.path = {sys.path}")
    except Exception as e:
        st.error(f"⚠️ Erreur: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

