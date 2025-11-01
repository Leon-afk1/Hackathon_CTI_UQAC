"""
Script de test pour le module data_retriever.
Permet de tester la récupération de données sans lancer Streamlit.
"""

from data_retriever import data_retriever

def test_database_connection():
    """Teste la connexion à la base de données."""
    print("=" * 60)
    print("TEST 1: Connexion à la base de données")
    print("=" * 60)
    try:
        schema = data_retriever.get_database_schema()
        print("✅ Connexion réussie!")
        print("\nSchéma de la base de données:")
        print(schema[:500] + "...")
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
    print()

def test_search_events():
    """Teste la recherche d'événements."""
    print("=" * 60)
    print("TEST 2: Recherche d'événements")
    print("=" * 60)
    try:
        query = "Quels sont les événements récents?"
        context = data_retriever.search_relevant_data(query)
        print(f"Query: {query}")
        print(f"\nContexte récupéré:\n{context}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    print()

def test_search_risks():
    """Teste la recherche de risques."""
    print("=" * 60)
    print("TEST 3: Recherche de risques")
    print("=" * 60)
    try:
        query = "Liste les risques avec une gravité élevée"
        context = data_retriever.search_relevant_data(query)
        print(f"Query: {query}")
        print(f"\nContexte récupéré:\n{context}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    print()

def test_search_measures():
    """Teste la recherche de mesures correctives."""
    print("=" * 60)
    print("TEST 4: Recherche de mesures correctives")
    print("=" * 60)
    try:
        query = "Quelles mesures correctives ont été mises en place?"
        context = data_retriever.search_relevant_data(query)
        print(f"Query: {query}")
        print(f"\nContexte récupéré:\n{context}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    print()

def test_general_stats():
    """Teste la récupération des statistiques générales."""
    print("=" * 60)
    print("TEST 5: Statistiques générales")
    print("=" * 60)
    try:
        query = "Donne-moi un aperçu général de la base de données"
        context = data_retriever.search_relevant_data(query)
        print(f"Query: {query}")
        print(f"\nContexte récupéré:\n{context}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    print()

if __name__ == "__main__":
    print("\n🔍 TEST DU MODULE DATA_RETRIEVER\n")
    
    test_database_connection()
    test_search_events()
    test_search_risks()
    test_search_measures()
    test_general_stats()
    
    print("=" * 60)
    print("✅ Tests terminés!")
    print("=" * 60)
