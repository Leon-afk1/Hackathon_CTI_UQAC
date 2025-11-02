"""
Utilitaires pour la gestion de la mémoire conversationnelle.
Inclut la synthèse d'historique et la détection de pertinence.
"""

import re
from typing import List, Dict, Any

def extract_key_info(text: str) -> str:
    """
    Extrait les informations clés d'un texte (IDs, noms, chiffres importants).
    """
    key_info = []
    
    # Extraire les IDs (event_id, person_id, etc.)
    ids = re.findall(r'(?:event_id|person_id|risk_id|measure_id|unit_id)[:\s]*(\d+)', text, re.IGNORECASE)
    if ids:
        key_info.append(f"IDs: {', '.join(set(ids))}")
    
    # Extraire les noms de personnes (pattern: Prénom Nom ou name: X, family_name: Y)
    names = re.findall(r'(?:name|nom)[:\s]*([A-Z][a-zà-ÿ]+)(?:\s+|.*?family_name[:\s]*)([A-Z][a-zà-ÿ]+)', text, re.IGNORECASE)
    if names:
        key_info.append(f"Personnes: {', '.join([f'{n[0]} {n[1]}' for n in names[:3]])}")
    
    # Extraire les types d'événements
    types = re.findall(r'(?:type|classification)[:\s]*([A-Za-zà-ÿ\s]+?)(?:\n|,|$)', text, re.IGNORECASE)
    if types:
        clean_types = [t.strip() for t in types[:3] if t.strip()]
        key_info.append(f"Types: {', '.join(clean_types)}")
    
    # Extraire les chiffres importants
    numbers = re.findall(r'(?:coût|cout|cost|nombre|count)[:\s]*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
    if numbers:
        key_info.append(f"Chiffres: {', '.join(numbers[:3])}")
    
    return " | ".join(key_info) if key_info else text[:100]


def synthesize_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Synthétise l'historique en gardant les infos clés si trop long.
    PRIORITÉ: Le dernier prompt est le plus important !
    Garde le dernier en entier, synthétise le reste.
    """
    if len(history) <= 2:
        return history
    
    synthesized = []
    
    # Si historique > 3, ne garder que le premier (contexte initial)
    if len(history) > 3:
        synthesized.append({
            "question": extract_key_info(history[0].get("question", "")),
            "sql": extract_key_info(history[0].get("sql", ""))[:100],
            "result": extract_key_info(history[0].get("result", ""))[:100],
            "assistant_response": ""
        })
    else:
        # Garder le premier avec plus de détails
        synthesized.append(history[0])
    
    # Synthétiser les échanges du milieu (très compacts)
    for exchange in history[1:-1]:
        synthesized.append({
            "question": exchange.get("question", "")[:80],
            "sql": extract_key_info(exchange.get("sql", ""))[:60],
            "result": "",  # Retirer les résultats du milieu
            "assistant_response": ""
        })
    
    # PRIORITÉ ABSOLUE: Garder le dernier échange COMPLET
    synthesized.append(history[-1])
    
    return synthesized


def is_question_related(current_question: str, previous_questions: List[str]) -> bool:
    """
    Détermine si la question actuelle est liée aux questions précédentes.
    
    Retourne True si:
    - Contient des mots de référence ("cette", "cet", "lui", "elle", "ça")
    - Contient des mots de continuation ("aussi", "également", "et", "puis")
    - Questions courtes (< 30 chars, probablement une suite)
    - Contient des IDs mentionnés avant
    
    Retourne False si:
    - Question complète et indépendante
    - Changement de sujet évident
    """
    if not previous_questions:
        return False
    
    current_lower = current_question.lower()
    
    # Mots de référence qui indiquent une continuité
    reference_words = [
        "cette", "cet", "ce", "celui", "celle", "ceux",
        "lui", "elle", "eux", "leur", "leurs",
        "ça", "cela", "celui-là", "celle-là",
        "même", "aussi", "également", "encore",
        "et", "puis", "après", "ensuite",
        "autres", "autre", "pareil", "similaire"
    ]
    
    # Si contient des mots de référence, c'est probablement lié
    for word in reference_words:
        if f" {word} " in f" {current_lower} " or current_lower.startswith(word):
            return True
    
    # Si question très courte (< 25 chars), probablement une continuation
    if len(current_question.strip()) < 25:
        return True
    
    # Vérifier si contient des IDs mentionnés dans les questions précédentes
    current_ids = set(re.findall(r'\b\d+\b', current_question))
    if current_ids:  # Si la question contient des IDs
        for prev_q in previous_questions[-2:]:  # Vérifier seulement les 2 dernières
            prev_ids = set(re.findall(r'\b\d+\b', prev_q))
            if current_ids & prev_ids:  # Intersection non vide
                return True
    
    # Mots qui indiquent CLAIREMENT un nouveau sujet
    new_topic_starters = [
        "liste", "liste-moi", "donne-moi",
        "montre", "montre-moi", "affiche",
        "trouve", "trouve-moi", "cherche",
        "combien de", "combien y", "quel est le nombre",
        "quels sont les", "quelles sont les",
        "qui sont les", "tous les", "toutes les"
    ]
    
    # Si commence clairement par une nouvelle question
    for starter in new_topic_starters:
        if current_lower.startswith(starter):
            # Exception: si contient aussi un mot de référence explicite
            explicit_refs = ["cette", "celui", "celle", "même", "aussi", "également"]
            if any(ref in current_lower for ref in explicit_refs):
                return True
            # Sinon c'est un nouveau sujet
            return False
    
    # Par défaut, considérer comme lié seulement si question très courte ou avec références
    if len(current_question) < 40:
        return True
    
    return False  # Questions longues sans mots de référence = nouveau sujet


def prepare_context_for_sql(history: List[Dict[str, Any]], current_question: str) -> List[Dict[str, Any]]:
    """
    Prépare le contexte à envoyer au générateur SQL.
    - Synthétise si trop long
    - Vide si question non liée
    """
    if not history:
        return []
    
    # Extraire les questions précédentes
    previous_questions = [ex.get("question", "") for ex in history]
    
    # Vérifier si la question est liée
    if not is_question_related(current_question, previous_questions):
        print(f"🔍 Question indépendante détectée, mémoire non utilisée")
        return []
    
    # Synthétiser si historique trop long
    if len(history) > 3:
        print(f"🔄 Synthèse de l'historique: {len(history)} → 3-4 échanges clés")
        return synthesize_history(history)
    
    return history
