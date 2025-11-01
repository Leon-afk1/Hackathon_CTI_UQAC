"""
Test de la mémoire conversationnelle du chatbot SQL.
Simule une conversation avec des références contextuelles.
"""

from sql_generator import sql_generator
from data_retriever import data_retriever

def test_conversation():
    """Teste une conversation avec contexte."""
    
    # Simuler un historique de conversation
    conversation_history = []
    
    # Question 1: Demander un événement spécifique
    print("\n" + "="*80)
    print("👤 USER: Donne-moi les infos sur l'événement 1")
    print("="*80)
    
    result1 = data_retriever.search_relevant_data(
        "Donne-moi les infos sur l'événement 1",
        conversation_history
    )
    
    print(f"\n✅ Succès: {result1['success']}")
    print(f"📝 SQL: {result1.get('sql_raw', 'N/A')}")
    print(f"📊 Résultats (extrait): {result1['context'][:300]}")
    
    # Ajouter à l'historique
    conversation_history.append({
        "question": "Donne-moi les infos sur l'événement 1",
        "sql": result1.get('sql_raw', ''),
        "result": result1['context'][:500]
    })
    
    # Question 2: Référence contextuelle (devrait comprendre "cet événement")
    print("\n" + "="*80)
    print("👤 USER: Qui sont les personnes impliquées dans cet événement?")
    print("="*80)
    
    result2 = data_retriever.search_relevant_data(
        "Qui sont les personnes impliquées dans cet événement?",
        conversation_history
    )
    
    print(f"\n✅ Succès: {result2['success']}")
    print(f"📝 SQL: {result2.get('sql_raw', 'N/A')}")
    print(f"🔍 Le SQL contient-il 'event_id = 1'? {('event_id = 1' in result2.get('sql_raw', ''))}")
    print(f"📊 Résultats (extrait): {result2['context'][:300]}")
    
    # Ajouter à l'historique
    conversation_history.append({
        "question": "Qui sont les personnes impliquées dans cet événement?",
        "sql": result2.get('sql_raw', ''),
        "result": result2['context'][:500]
    })
    
    # Question 3: Référence à une personne mentionnée
    print("\n" + "="*80)
    print("👤 USER: Quels autres événements cette personne a déclaré?")
    print("="*80)
    print("(Note: Le chatbot devrait chercher le nom de la personne dans l'historique)")
    
    result3 = data_retriever.search_relevant_data(
        "Quels autres événements cette personne a déclaré?",
        conversation_history
    )
    
    print(f"\n✅ Succès: {result3['success']}")
    print(f"📝 SQL: {result3.get('sql_raw', 'N/A')}")
    print(f"🔄 Tentatives: {result3.get('attempts', 1)}")
    
    print("\n" + "="*80)
    print("📋 RÉSUMÉ:")
    print(f"- Nombre d'échanges: {len(conversation_history)}")
    print(f"- Historique maintenu: {min(5, len(conversation_history))} échanges")
    print("="*80)


if __name__ == "__main__":
    test_conversation()
