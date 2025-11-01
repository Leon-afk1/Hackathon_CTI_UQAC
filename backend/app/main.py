####TEST ONLY

import os
import psycopg2
from flask import Flask, jsonify
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

def get_db_connection():
    """Établit une connexion à la base de données PostgreSQL."""
    conn = psycopg2.connect(
        host="db",  # Le nom du service de la base de données dans docker-compose
        dbname=os.environ.get("POSTGRES_DB"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )
    return conn

@app.route('/')
def index():
    return "Le backend Python fonctionne !"

@app.route('/test-db')
def test_db():
    """Teste la connexion à la base de données et récupère la version de PostgreSQL."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT version()')
        db_version = cur.fetchone()
        cur.close()
        conn.close()
        return jsonify({"message": "Connexion à la base de données réussie !", "version": db_version})
    except Exception as e:
        return jsonify({"message": "Erreur de connexion à la base de données.", "error": str(e)}), 500

# --- NOUVELLE ROUTE ---
@app.route('/events')
def get_events():
    """Récupère les 5 premiers événements de la base de données."""
    try:
        conn = get_db_connection()
        # RealDictCursor permet d'obtenir les résultats sous forme de dictionnaires (clé: valeur)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Exécution de la requête simple
        cur.execute('SELECT * FROM public.event ORDER BY event_id DESC LIMIT 5')
        
        # Récupération de tous les résultats
        events = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Retourne les résultats au format JSON
        return jsonify(events)
        
    except Exception as e:
        return jsonify({"message": "Erreur lors de la récupération des événements.", "error": str(e)}), 500
# --- FIN DE LA NOUVELLE ROUTE ---

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)