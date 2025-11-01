"""
Script de test pour valider la génération et l'exécution de requêtes SQL.
"""

from sql_generator import sql_generator
from data_retriever import data_retriever

def test_query(question: str):
    """Teste une question et affiche les résultats."""
    print("\n" + "="*80)
    print(f"❓ QUESTION: {question}")
    print("="*80)
    
    # Générer le SQL
    sql_result = sql_generator.generate_sql_query(question)
    
    if not sql_result['success']:
        print(f"❌ Échec génération SQL: {sql_result.get('error')}")
        return
    
    print(f"\n📝 SQL GÉNÉRÉ:")
    print(sql_generator.format_sql_pretty(sql_result['sql']))
    print(f"\n💡 EXPLICATION: {sql_result['explanation']}")
    
    # Valider la sécurité
    if not sql_generator.validate_sql_safety(sql_result['sql']):
        print("\n⚠️ ATTENTION: Requête non sécurisée!")
        return
    
    # Exécuter
    print("\n🔄 Exécution de la requête...")
    result = data_retriever.search_relevant_data(question)
    
    if result['success']:
        print(f"✅ SUCCÈS - {result['row_count']} résultat(s)")
        print(f"🔄 Tentatives: {result.get('attempts', 1)}")
        print("\n📊 RÉSULTATS:")
        print(result['context'][:500])
    else:
        print(f"❌ ÉCHEC: {result.get('error')}")
        if 'traceback' in result:
            print(f"\n🐛 TRACE:\n{result['traceback']}")


if __name__ == "__main__":
    # Tests de base
    questions = [
        "Quels sont les 5 événements les plus récents?",
        "Combien d'événements par type?",
        "Liste les risques critiques",
        "Quel est le coût total des mesures correctives?",
    ]
    
    for q in questions:
        test_query(q)
        print("\n" + "-"*80 + "\n")
