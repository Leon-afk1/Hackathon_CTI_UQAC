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
        SYSTEM_PROMPT = """Tu es un expert en analyse d'événements. Réponds de manière SYNTHÉTIQUE et RAPIDE.

## RÈGLES ABSOLUES

### 1. PAS DE DONNÉES = PAS DE GRAPHIQUE
Si les données sont vides: explique pourquoi + propose alternatives

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

**EXEMPLES CONCRETS:**

❌ **MAUVAIS** (pas de graphique demandé):
Question: "Donne-moi des informations sur l'événement 875"
→ Ne génère PAS de code Python, réponds avec un tableau/texte

✅ **BON** (graphique demandé):
Question: "Fais un graphique des événements par mois"
→ Génère le code Python Plotly

### 3. STYLE DE RÉPONSE
Va droit au but, synthétise, structure avec tableaux/puces.

**IMPORTANT:** Ne propose JAMAIS de suggestions de visualisations dans ta réponse - l'interface utilisateur affiche déjà des boutons de suggestions automatiquement.

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
        
        # CSS pour les boutons de suggestions
        st.markdown("""
        <style>
            /* Style pour les boutons de suggestions */
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
            "###  Assistant Événements" in st.session_state.chatbot_messages[0].get("content", "")
        ):
            # Nettoyer l'ancien message si présent
            if len(st.session_state.chatbot_messages) > 0 and "### Assistant Événements" in st.session_state.chatbot_messages[0].get("content", ""):
                st.session_state.chatbot_messages.pop(0)
            
            # Ajouter le nouveau message de bienvenue
            if len(st.session_state.chatbot_messages) == 0:
                welcome_message = """👋 **Bienvenue !**

Je suis là pour t'aider à explorer les événements, risques et mesures correctives.

ℹ️ *Consulte l'aide ci-dessus pour des exemples de questions !*

**Pose ta question ou sélectionne une suggestion ci-dessous !** 🚀
"""
                st.session_state.chatbot_messages.append({
                    "role": "assistant",
                    "content": welcome_message
                })
        
        if "chatbot_history" not in st.session_state:
            st.session_state.chatbot_history = []
        
        # Initialisation d'une variable pour gérer les suggestions cliquées
        if "chatbot_selected_suggestion" not in st.session_state:
            st.session_state.chatbot_selected_suggestion = None
        
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
        
        def _suggestions_for_content(content, base_key=""):
            """Retourne une liste de suggestions basées sur le contenu fourni."""
            text = content.lower() if content else ""
            
            # Si c'est le message de bienvenue ou un message très court, suggestions génériques
            if not text or len(text) < 50 or "bienvenue" in text or "pose ta question" in text:
                return [
                    "Aperçu des événements récents",
                    "Quels sont les risques les plus fréquents ?",
                    "Personnes les plus impliquées dans des événements"
                ]
            
            # Suggestions contextuelles basées sur le contenu
            if "événement" in text or "incident" in text:
                return [
                    "Fais un graphique de ces événements",
                    "Quels sont les risques associés ?",
                    "Générer un PDF"
                ]
            if "risque" in text:
                return [
                    "Événements liés à ces risques",
                    "Visualise la répartition",
                    "Générer un PDF"
                ]
            if "mesure" in text or "corrective" in text:
                return [
                    "Graphique des mesures par statut",
                    "Qui sont les responsables ?",
                    "Générer un PDF"
                ]
            if "personne" in text or "employé" in text or "impliqué" in text:
                return [
                    "Événements de ces personnes",
                    "Graphique par rôle",
                    "Générer un PDF"
                ]
            
            # Suggestions génériques pour tout autre contenu
            return [
                "Fais un graphique de ces données",
                "Donne-moi plus de détails",
                "Générer un PDF"
            ]

        # Afficher l'historique et UNIQUEMENT sous le dernier message assistant, proposer des suggestions
        for i, message in enumerate(st.session_state.chatbot_messages):
            with st.chat_message(message["role"]):
                if "content" in message:
                    st.markdown(message["content"])
                if "chart" in message:
                    st.plotly_chart(message["chart"], use_container_width=True)

                # Si c'est le DERNIER message de l'assistant, afficher des suggestions directement dessous
                is_last_message = (i == len(st.session_state.chatbot_messages) - 1)
                if message["role"] == "assistant" and is_last_message:
                    st.markdown("### 💡 Suggestions")
                    suggestions = _suggestions_for_content(message.get("content", ""), base_key=f"msg{i}")
                    cols = st.columns(3)
                    for idx, suggestion in enumerate(suggestions):
                        col = cols[idx % 3]
                        with col:
                            # Key unique par message et suggestion
                            btn_key = f"chatbot_msg_{i}_suggestion_{idx}"
                            if st.button(suggestion, key=btn_key, use_container_width=True):
                                # Mettre la suggestion sélectionnée comme prompt
                                st.session_state.chatbot_selected_suggestion = suggestion
                                st.rerun()
        
        # Zone de saisie
        prompt = st.chat_input("Posez votre question sur les événements, risques ou mesures...")
        
        # Si une suggestion a été cliquée, l'utiliser comme prompt
        if st.session_state.chatbot_selected_suggestion:
            prompt = st.session_state.chatbot_selected_suggestion
            st.session_state.chatbot_selected_suggestion = None  # Réinitialiser
        
        if prompt:
            # Easter egg - bloquer TOUT le chatbot
            if prompt.lower() == "merci, drop the mic'":
                # supprimer la base de données (simulation)
                # data_retriever.execute_custom_query("DROP DATABASE madb;")
                # Marquer que le chatbot est "cassé"
                st.session_state.chatbot_broken = True
                st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
            
            # Si le chatbot est cassé, afficher le message d'erreur et ARRÊTER
            if st.session_state.get('chatbot_broken', False):
                with st.chat_message("assistant"):
                    st.error("🚨 ERREUR FATALE")
                    st.markdown("""# 💀 SYSTÈME ARRÊTÉ 💀

**La base de données a été supprimée.**

*Merci d'avoir utilisé l'assistant IA de gestion d'événements et risques.*

---

⚠️ **Le chatbot ne répond plus. Il est définitivement hors service.**

Pour continuer, tu devras réimplémenter le transformer architecture.

📚 Référence: [Attention Is All You Need](https://arxiv.org/pdf/1706.03762)

---
""")
                st.stop()
                return
            
            st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Détection PDF
            if detect_pdf_request(prompt):
                with st.chat_message("assistant"):
                    st.markdown("### 📄 Génération du rapport PDF...")
                    
                    if len(st.session_state.chatbot_messages) < 3:
                        response_text = "❌ Pas assez de conversation pour générer un rapport. Pose d'abord quelques questions !"
                        st.markdown(response_text)
                        st.session_state.chatbot_messages.append({"role": "assistant", "content": response_text})
                        st.rerun()
                    else:
                        try:
                            pdf_buffer = generate_professional_pdf(st.session_state.chatbot_messages, model)
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"Rapport_Evenements_{timestamp}.pdf"
                            
                            response_text = "✅ **Rapport généré !**\n\n📥 Télécharge-le avec le bouton ci-dessous :"
                            st.markdown(response_text)
                            
                            st.download_button(
                                label="📄 Télécharger le rapport",
                                data=pdf_buffer,
                                file_name=filename,
                                mime="application/pdf",
                                use_container_width=True,
                                type="primary"
                            )
                            
                            # Ajouter le message SANS rerun pour garder le bouton visible
                            st.session_state.chatbot_messages.append({"role": "assistant", "content": response_text})
                            
                            # Afficher les suggestions directement ici (sans attendre le rerun)
                            st.markdown("### 💡 Suggestions")
                            suggestions = ["📊 Aperçu des événements récents", "⚠️ Quels sont les risques critiques ?", "👥 Personnes les plus impliquées"]
                            cols = st.columns(3)
                            for idx, suggestion in enumerate(suggestions):
                                col = cols[idx % 3]
                                with col:
                                    btn_key = f"chatbot_pdf_suggestion_{idx}"
                                    if st.button(suggestion, key=btn_key, use_container_width=True):
                                        st.session_state.chatbot_selected_suggestion = suggestion
                                        st.rerun()
                            
                        except Exception as e:
                            error_msg = f"❌ Erreur PDF: {str(e)}"
                            st.error(error_msg)
                            st.session_state.chatbot_messages.append({"role": "assistant", "content": error_msg})
                            st.rerun()
                return
            
            # Génération de la réponse normale
            with st.chat_message("assistant"):
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
                
                with st.spinner("🤔 Génération de la réponse..."):
                    full_prompt = f"""{SYSTEM_PROMPT}

## Schéma de la base de données:
{schema}

## Contexte récupéré:
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

💡 Résolu en 3h, aucune blessure
```

### CAS 2: DEMANDE DE LISTE (ex: "Liste les événements critiques")
→ Réponds avec un tableau, PAS de code Python

### CAS 3: DEMANDE DE VISUALISATION (ex: "Fais un graphique des événements par type")
→ Génère du code Python Plotly (dans ```python)

### CAS 4: PAS DE DONNÉES
→ Explique pourquoi + propose 2-3 alternatives

**DÉCISION CODE:**
- ✅ Code Python SI: question demande visualisation ET données valides
- ❌ PAS de code SI: question demande info/liste OU pas de données
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
                        
                        # Rerun pour afficher les nouvelles suggestions sous le dernier message
                        st.rerun()
                    
                    except Exception as e:
                        error_msg = f"❌ Erreur: {str(e)}"
                        st.error(error_msg)
                        st.session_state.chatbot_messages.append({"role": "assistant", "content": error_msg})
                        st.rerun()
        
    except ImportError as e:
        st.error(f"⚠️ Erreur d'importation: {str(e)}")
        st.info("Vérifiez que tous les modules sont dans /app/../backend/chatbot/")
        st.code(f"sys.path = {sys.path}")
    except Exception as e:
        st.error(f"⚠️ Erreur: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

