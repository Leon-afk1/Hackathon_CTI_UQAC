"""
Application Streamlit pour un chatbot RAG utilisant Gemini
avec accès à la base de données PostgreSQL d'événements.
"""

import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai
from data_retriever import data_retriever

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

# Prompt système pour le chatbot
SYSTEM_PROMPT = """Tu es un expert en analyse d'événements. Réponds de manière SYNTHÉTIQUE et RAPIDE.

## BASE DE DONNÉES
- event (événements centraux)
- person (employés)
- risk (risques)  
- corrective_measure (actions)
- organizational_unit (services)
- Tables liaison: event_employee, event_risk, event_corrective_measure

## STYLE DE RÉPONSE
1. **VA DROIT AU BUT** - L'utilisateur veut une info rapide
2. **SYNTHÉTISE** - Résume, n'étale pas
3. **STRUCTURE** - Tableaux courts, puces, chiffres clés
4. **EXPLIQUE** - Dis ce que tu as trouvé et pourquoi c'est important
5. **SOIS PRÉCIS** - Cite les IDs, noms, chiffres exacts

## EXEMPLES

❌ MAL: "Bien sûr ! Je suis ravi de vous aider. Voici une liste exhaustive de tous les événements..."

✅ BIEN: "**5 événements récents:**
| ID | Description | Date | Type |
|---|---|---|---|
| 125 | Panne ligne A | 28/10 | Incident |

💡 3 sont critiques, 2 résolus"

## TON APPROCHE
- Commence direct (pas de "bien sûr, je serais ravi...")
- Mets les chiffres importants en avant
- Propose une action si pertinent
- Si pas de données: dis-le et propose alternative
"""

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
    - "Mesures en cours ?"
    - "Qui a déclaré le plus d'événements ?"
    """)
    
    st.divider()
    

    
    if st.button("🔄 Réinitialiser"):
        st.session_state.messages = []
        st.rerun()

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
- "Qui dans événement 5?"
- "Coût total mesures"

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
        st.markdown(message["content"])

# Zone de saisie utilisateur
if prompt := st.chat_input("Posez votre question sur les événements, risques ou mesures..."):
    # Ajout du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Génération de la réponse
    with st.chat_message("assistant"):
        # Afficher un indicateur si on utilise l'historique
        history_size = len(st.session_state.conversation_history)
        if history_size > 0:
            with st.expander(f"🧠 Mémoire active: {history_size} échange(s) précédent(s)", expanded=False):
                for i, ex in enumerate(st.session_state.conversation_history[-3:], 1):
                    st.caption(f"{i}. Q: {ex.get('question', 'N/A')[:60]}...")
        
        with st.spinner("🔍 Analyse de la question et génération de la requête SQL..."):
            # Récupération du contexte depuis la base de données avec SQL intelligent
            # On passe les 5 derniers échanges comme historique
            search_result = data_retriever.search_relevant_data(
                prompt, 
                st.session_state.conversation_history[-5:]  # Garde seulement les 5 derniers
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

## Question utilisateur:
{prompt}

## FORMAT RÉPONSE:

**STRUCTURE OBLIGATOIRE:**
1. Résumé en 1 ligne (chiffre clé)
2. Tableau compact (max 5 colonnes essentielles)
3. Insight/observation importante (1 phrase avec 💡)

**EXEMPLE:**
```
**15 événements trouvés** (10 derniers affichés)

| ID | Description | Date | Type |
|---|---|---|---|
| 125 | Panne ligne A | 28/10 | Incident |
| 124 | Chute escalier | 27/10 | Accident |

💡 40% sont de type "Incident", majoritairement résolus
```

**RÈGLES:**
- Max 10 lignes de tableau
- Dates format court: JJ/MM
- Pas de phrases longues
- Mets en gras les chiffres importants
- Si >10 résultats: indique le total mais affiche que 10
"""
            
            try:
                # Génération de la réponse avec Gemini
                response = model.generate_content(full_prompt)
                assistant_response = response.text
                
                # Affichage de la réponse
                st.markdown(assistant_response)
                
                # Ajout à l'historique des messages
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                
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
