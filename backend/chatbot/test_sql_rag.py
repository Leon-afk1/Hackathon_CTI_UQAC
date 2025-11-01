"""
Script de test pour le SQL Generator et le système RAG complet.
"""

from sql_generator import sql_generator
from data_retriever import data_retriever

def test_sql_generation():
    """Teste la génération de requêtes SQL."""
    print("=" * 80)
    print("TEST DU SQL GENERATOR")
    print("=" * 80)
    
    questions = [
        "Quels sont les événements récents ?",
        "Liste les risques identifiés",
        "Quelles mesures correctives sont en cours ?",
        "Qui sont les personnes impliquées dans l'événement 5 ?",
        "Donne-moi les informations sur le risque de gravité élevée",
        "Combien d'événements ont été déclarés ?",
        "Quels sont les événements avec des risques critiques ?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"QUESTION {i}: {question}")
        print(f"{'='*80}")
        
        result = sql_generator.generate_sql_query(question)
        
        if result['success']:
            print(f"\n✅ SQL généré avec succès!")
            print(f"\n📝 EXPLICATION:\n{result['explanation']}")
            print(f"\n💻 SQL:")
            print("-" * 80)
            print(result['sql'])
            print("-" * 80)
            
            # Valider la sécurité
            is_safe = sql_generator.validate_sql_safety(result['sql'])
            print(f"\n🔒 Sécurité: {'✅ OK' if is_safe else '❌ DANGER'}")
        else:
            print(f"\n❌ Échec de la génération SQL")
            print(f"Erreur: {result.get('error', 'Inconnue')}")
        
        print()

def test_data_retrieval():
    """Teste la récupération complète des données (SQL + formatage)."""
    print("\n" + "=" * 80)
    print("TEST DE RÉCUPÉRATION DE DONNÉES COMPLÈTE")
    print("=" * 80)
    
    questions = [
        "Quels sont les événements récents ?",
        "Liste les risques identifiés",
        "Quelles mesures correctives sont en cours ?",
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'='*80}")
        print(f"QUESTION {i}: {question}")
        print(f"{'='*80}")
        
        try:
            result = data_retriever.search_relevant_data(question)
            
            if result['success']:
                print(f"\n✅ Requête exécutée avec succès!")
                print(f"📊 Nombre de résultats: {result.get('row_count', 0)}")
                
                if result.get('sql_used'):
                    print(f"\n💻 SQL utilisé:")
                    print("-" * 80)
                    print(result['sql_used'])
                    print("-" * 80)
                
                print(f"\n📋 CONTEXTE RÉCUPÉRÉ:")
                print("-" * 80)
                context = result['context']
                # Limiter l'affichage pour la lisibilité
                if len(context) > 1000:
                    print(context[:1000] + "\n... (tronqué)")
                else:
                    print(context)
                print("-" * 80)
            else:
                print(f"\n❌ Échec de la requête")
                print(f"Erreur: {result.get('error', 'Inconnue')}")
                if 'context' in result:
                    print(f"Contexte (fallback): {result['context'][:500]}")
        
        except Exception as e:
            print(f"\n❌ Exception: {str(e)}")
        
        print()

def test_safety_validation():
    """Teste la validation de sécurité SQL."""
    print("\n" + "=" * 80)
    print("TEST DE VALIDATION DE SÉCURITÉ SQL")
    print("=" * 80)
    
    test_queries = [
        ("SELECT * FROM event LIMIT 10", True, "Requête SELECT simple"),
        ("DROP TABLE event", False, "Tentative de DROP"),
        ("DELETE FROM event WHERE event_id = 1", False, "Tentative de DELETE"),
        ("SELECT * FROM event; DROP TABLE event;", False, "Injection SQL"),
        ("UPDATE event SET description = 'test'", False, "Tentative d'UPDATE"),
        ("INSERT INTO event VALUES (1, 'test')", False, "Tentative d'INSERT"),
        ("WITH cte AS (SELECT * FROM event) SELECT * FROM cte", True, "CTE valide"),
    ]
    
    for sql, expected, description in test_queries:
        is_safe = sql_generator.validate_sql_safety(sql)
        status = "✅" if is_safe == expected else "❌"
        print(f"\n{status} {description}")
        print(f"   SQL: {sql[:60]}...")
        print(f"   Résultat: {'SAFE' if is_safe else 'DANGEROUS'} (attendu: {'SAFE' if expected else 'DANGEROUS'})")

if __name__ == "__main__":
    print("\n" + "🚀" * 40)
    print("TEST COMPLET DU SYSTÈME RAG AVEC SQL GENERATOR")
    print("🚀" * 40 + "\n")
    
    try:
        # Test 1: Génération SQL
        test_sql_generation()
        
        # Test 2: Validation de sécurité
        test_safety_validation()
        
        # Test 3: Récupération complète
        test_data_retrieval()
        
        print("\n" + "=" * 80)
        print("✅ TOUS LES TESTS SONT TERMINÉS")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {str(e)}")
        import traceback
        traceback.print_exc()
