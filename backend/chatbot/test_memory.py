"""
Test des utilitaires de mémoire:
- Détection de questions liées/non liées
- Synthèse d'historique
"""

from memory_utils import is_question_related, synthesize_history, extract_key_info

def test_question_detection():
    """Teste la détection de questions liées."""
    
    print("\n" + "="*80)
    print("TEST 1: Détection de questions liées vs non liées")
    print("="*80)
    
    previous_questions = [
        "Donne-moi les infos sur l'événement 102",
        "Qui sont les personnes impliquées?"
    ]
    
    test_cases = [
        # Questions liées (doivent retourner True)
        ("Et les risques associés?", True, "Question courte de continuation"),
        ("Donne-moi les infos sur cette personne", True, "Référence: 'cette personne'"),
        ("Quels autres événements lui sont associés?", True, "Référence: 'lui'"),
        ("Montre-moi aussi les mesures", True, "Mot de continuation: 'aussi'"),
        ("Événement 102", True, "ID mentionné avant"),
        
        # Questions non liées (doivent retourner False)
        ("Combien d'événements de type Accident au total?", False, "Question complète indépendante"),
        ("Liste tous les risques de gravité élevée", False, "Nouveau sujet sans référence"),
        ("Donne-moi les statistiques globales des événements", False, "Changement de sujet"),
    ]
    
    for question, expected, reason in test_cases:
        result = is_question_related(question, previous_questions)
        status = "✅" if result == expected else "❌"
        print(f"\n{status} Question: \"{question}\"")
        print(f"   Attendu: {expected}, Obtenu: {result}")
        print(f"   Raison: {reason}")


def test_synthesis():
    """Teste la synthèse d'historique."""
    
    print("\n\n" + "="*80)
    print("TEST 2: Synthèse d'historique long")
    print("="*80)
    
    # Créer un historique de 5 échanges
    long_history = [
        {
            "question": "Événement 102",
            "sql": "SELECT e.event_id, e.description, e.type FROM event e WHERE e.event_id = 102",
            "result": "event_id: 102, description: Panne électrique, type: Incident, declared_by: Jean Dupont"
        },
        {
            "question": "Qui l'a déclaré?",
            "sql": "SELECT p.name, p.family_name FROM person p JOIN event e ON e.declared_by_id = p.person_id WHERE e.event_id = 102",
            "result": "name: Jean, family_name: Dupont, role: Technicien"
        },
        {
            "question": "Quels autres événements il a déclarés?",
            "sql": "SELECT e.event_id, e.description FROM event e JOIN person p ON e.declared_by_id = p.person_id WHERE p.name = 'Jean' AND p.family_name = 'Dupont'",
            "result": "event_id: 102, 103, 105; Total: 3 événements"
        },
        {
            "question": "Et les risques de l'événement 102?",
            "sql": "SELECT r.name, r.gravity FROM risk r JOIN event_risk er ON r.risk_id = er.risk_id WHERE er.event_id = 102",
            "result": "risk: Électrocution, gravity: Élevée; risk: Incendie, gravity: Moyenne"
        },
        {
            "question": "Quel est le coût des mesures correctives?",
            "sql": "SELECT SUM(cm.cost) FROM corrective_measure cm JOIN event_corrective_measure ecm ON cm.measure_id = ecm.measure_id WHERE ecm.event_id = 102",
            "result": "cost: 1500.00 euros"
        }
    ]
    
    print(f"\n📊 Historique original: {len(long_history)} échanges")
    
    synthesized = synthesize_history(long_history)
    
    print(f"📊 Historique synthétisé: {len(synthesized)} échanges")
    print(f"\nStructure:")
    print(f"  - 2 premiers échanges gardés en entier")
    print(f"  - {len(long_history) - 3} échanges du milieu synthétisés")
    print(f"  - Dernier échange gardé en entier")
    
    print("\n🔍 Aperçu synthèse:")
    for i, ex in enumerate(synthesized, 1):
        print(f"\n{i}. Q: {ex['question'][:50]}...")
        if len(ex.get('sql', '')) < 100:
            print(f"   SQL synthétisé: {ex['sql'][:80]}...")


def test_extraction():
    """Teste l'extraction d'infos clés."""
    
    print("\n\n" + "="*80)
    print("TEST 3: Extraction d'informations clés")
    print("="*80)
    
    test_texts = [
        "event_id: 102, description: Panne électrique, type: Incident, declared_by: Jean Dupont, cost: 1500.50",
        "SELECT e.* FROM event e WHERE e.type = 'Accident' AND e.classification = 'Grave'",
        "Résultat: 15 événements trouvés. Types: Accident (8), Incident (7). Coût total: 25000 euros."
    ]
    
    for text in test_texts:
        extracted = extract_key_info(text)
        print(f"\n📝 Texte original ({len(text)} chars):")
        print(f"   {text[:80]}...")
        print(f"🔑 Infos extraites:")
        print(f"   {extracted}")


if __name__ == "__main__":
    test_question_detection()
    test_synthesis()
    test_extraction()
    
    print("\n\n" + "="*80)
    print("✅ Tests terminés")
    print("="*80)
