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
    Garde les 2 premiers et le dernier en entier, synthétise le milieu.
    """
    if len(history) <= 3:
        return history
    
    synthesized = []
    
    # Garder les 2 premiers en entier (contexte initial important)
    synthesized.extend(history[:2])
    
    # Synthétiser les échanges du milieu
    for exchange in history[2:-1]:
        synthesized.append({
            "question": exchange.get("question", ""),
            "sql": extract_key_info(exchange.get("sql", "")),
            "result": extract_key_info(exchange.get("result", "")),
            "assistant_response": extract_key_info(exchange.get("assistant_response", ""))
        })
    
    # Garder le dernier en entier (contexte immédiat)
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
    
    # Si question très courte (< 30 chars), probablement une continuation
    if len(current_question.strip()) < 30:
        return True
    
    # Vérifier si contient des IDs mentionnés dans les questions précédentes
    current_ids = set(re.findall(r'\b\d+\b', current_question))
    for prev_q in previous_questions[-3:]:  # Vérifier les 3 dernières
        prev_ids = set(re.findall(r'\b\d+\b', prev_q))
        if current_ids & prev_ids:  # Intersection non vide
            return True
    
    # Mots qui indiquent un nouveau sujet
    new_topic_words = [
        "combien", "liste", "donne", "montre", "affiche",
        "quels sont", "quel est", "qui sont", "qui est",
        "trouve", "cherche", "recherche"
    ]
    
    # Si commence par un mot de nouveau sujet et est assez long, c'est probablement indépendant
    if len(current_question) > 40:
        for word in new_topic_words:
            if current_lower.startswith(word):
                # Mais si contient aussi un mot de référence, c'est quand même lié
                if any(ref in current_lower for ref in reference_words):
                    return True
                return False
    
    # Par défaut, on considère que c'est lié (prudent)
    return True


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
