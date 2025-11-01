"""
Module pour générer des requêtes SQL à partir de questions en langage naturel.
Utilise Gemini pour traduire les questions en SQL.

SYSTÈME DE MÉMOIRE CONVERSATIONNELLE:
====================================
Le générateur SQL maintient un historique des 5 derniers échanges pour comprendre le contexte.

FONCTIONNALITÉS:
- ✅ Résolution de références ambiguës ("cette personne", "cet événement", "lui/elle")
- ✅ Continuation de conversation ("Et les risques?", "Combien ça coûte?")
- ✅ Retry automatique avec analyse d'erreur (max 5 tentatives)
- ✅ Formatage SQL lisible pour debug
- ✅ Validation et nettoyage automatique du SQL

EXEMPLE D'UTILISATION:
1. User: "Événement 102" → SQL retourne info avec "Jean Dupont"
2. User: "Donne les infos sur cette personne" → Comprend qu'il faut chercher Jean Dupont
3. User: "Quels événements il a déclarés?" → Utilise le nom de la personne de l'étape 2

LIMITES:
- Maximum 5 tentatives de génération SQL avant abandon
- Historique limité aux 5 derniers échanges
- Nécessite GEMINI_API_KEY configurée
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai
from typing import Optional, Dict, Any
import re

load_dotenv()

class SQLGenerator:
    """Générateur de requêtes SQL à partir de langage naturel."""
    
    def __init__(self):
        """Initialise le générateur SQL avec Gemini."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY non trouvée")
        
        genai.configure(api_key=api_key)
        try:
            self.model = genai.GenerativeModel('gemini-2.5-flash')
        except:
            self.model = genai.GenerativeModel('gemini-pro')
    
    def get_database_schema_detailed(self) -> str:
        """Retourne un schéma détaillé de la base de données pour la génération SQL."""
        return """
## SCHÉMA POSTGRESQL

### person (personnes)
- person_id (PK)
- matricule, name, family_name, role

### organizational_unit (unités)
- unit_id (PK)
- identifier, name, location

### event (événements - TABLE CENTRALE)
- event_id (PK)
- declared_by_id (FK → person.person_id)
- description (TEXT)
- start_datetime, end_datetime
- organizational_unit_id (FK → organizational_unit.unit_id)
- type, classification

### risk (risques)
- risk_id (PK)
- name, gravity, probability

### corrective_measure (mesures)
- measure_id (PK)
- name, description
- owner_id (FK → person.person_id)
- implementation_date, cost
- organizational_unit_id (FK → organizational_unit.unit_id)

### TABLES DE LIAISON:
- event_employee (event_id, person_id)
- event_risk (event_id, risk_id)
- event_corrective_measure (event_id, measure_id)

## EXEMPLES SQL CORRECTS:

-- Ex1: Événements récents avec détails
SELECT e.event_id, e.description, e.type, e.classification, 
       e.start_datetime, p.name || ' ' || p.family_name AS declarant,
       ou.name AS unite
FROM event e
LEFT JOIN person p ON e.declared_by_id = p.person_id
LEFT JOIN organizational_unit ou ON e.organizational_unit_id = ou.unit_id
ORDER BY e.start_datetime DESC 
LIMIT 10;

-- Ex2: Personnes impliquées dans événement spécifique
SELECT p.person_id, p.name, p.family_name, p.role
FROM person p
INNER JOIN event_employee ee ON p.person_id = ee.person_id
WHERE ee.event_id = 5;

-- Ex3: Statistiques par type d'événement (GROUP BY)
SELECT e.type, COUNT(*) AS nombre, 
       COUNT(DISTINCT e.declared_by_id) AS nb_declarants
FROM event e
GROUP BY e.type
ORDER BY nombre DESC;

-- Ex4: Risques critiques avec leurs événements
SELECT r.risk_id, r.name, r.gravity, r.probability,
       COUNT(er.event_id) AS nb_events
FROM risk r
LEFT JOIN event_risk er ON r.risk_id = er.risk_id
WHERE r.gravity = 'Élevée' OR r.gravity = 'Critique'
GROUP BY r.risk_id, r.name, r.gravity, r.probability
ORDER BY nb_events DESC;

-- Ex5: Coût total des mesures par unité
SELECT ou.name AS unite, 
       COUNT(cm.measure_id) AS nb_mesures,
       COALESCE(SUM(cm.cost), 0) AS cout_total
FROM organizational_unit ou
LEFT JOIN corrective_measure cm ON ou.unit_id = cm.organizational_unit_id
GROUP BY ou.unit_id, ou.name
ORDER BY cout_total DESC;
"""
    
    def generate_sql_query(self, question: str, conversation_history: list = None) -> Dict[str, Any]:
        """
        Génère une requête SQL à partir d'une question en langage naturel.
        
        Args:
            question: Question en langage naturel
            conversation_history: Liste des 5 derniers échanges [{role, content, sql}]
        
        Returns:
            Dict contenant 'sql', 'explanation', et 'success'
        """
        schema = self.get_database_schema_detailed()
        
        # Construire le contexte de conversation DÉTAILLÉ
        history_context = ""
        if conversation_history and len(conversation_history) > 0:
            history_context = "\n## 📚 HISTORIQUE CONVERSATION (pour CONTEXTE):\n\n"
            history_context += "**IMPORTANT:** Utilise cet historique pour comprendre les questions ambiguës.\n"
            history_context += "Si l'utilisateur dit 'cette personne', 'cet événement', 'lui', 'ça' → regarde l'historique!\n\n"
            
            for i, exchange in enumerate(conversation_history[-5:], 1):
                history_context += f"### Échange {i}:\n"
                history_context += f"**Question:** {exchange.get('question', 'N/A')}\n"
                
                if exchange.get('sql'):
                    history_context += f"**SQL utilisé:** {exchange.get('sql', '')}\n"
                
                if exchange.get('result'):
                    # Extraire les données clés de la réponse
                    result_preview = exchange.get('result', '')[:300]
                    history_context += f"**Résultat obtenu:** {result_preview}...\n"
                
                history_context += "\n"
            
            history_context += "**→ Utilise ces informations pour résoudre les références (noms, IDs, 'cette personne', etc.)**\n\n"
        
        prompt = f"""Tu es un expert en SQL et bases de données PostgreSQL.

Ton rôle est de traduire des questions en langage naturel en requêtes SQL valides.

{schema}

{history_context}

## 🎯 CONTEXTE ET MÉMOIRE:
**Si la question de l'utilisateur est ambiguë ou contient des références:**
- "cette personne", "lui", "elle" → Cherche le nom dans l'historique
- "cet événement", "celui-là" → Cherche l'event_id dans l'historique
- "le coût", "combien" sans précision → Regarde ce qui a été discuté avant
- Nombres isolés (ex: "102") → Probablement un ID mentionné avant

**Exemples de résolution avec contexte:**

**Cas 1: Référence à une personne**
- Échange précédent: "Événement 102" → Résultat: "Jean Dupont a déclaré cet événement"
- Question actuelle: "Donne les infos sur cette personne"
- SQL à générer: `SELECT * FROM person p WHERE p.name = 'Jean' AND p.family_name = 'Dupont';`

**Cas 2: Référence à un événement**
- Échange précédent: SQL contenait `WHERE e.event_id = 102`
- Question actuelle: "Quels sont les risques associés?"
- SQL à générer: `SELECT r.* FROM risk r JOIN event_risk er ON r.risk_id = er.risk_id WHERE er.event_id = 102;`

**Cas 3: Suite logique**
- Échange précédent: "Combien d'événements par type?" → Résultat: "Accident: 15, Incident: 23"
- Question actuelle: "Montre-moi les accidents"
- SQL à générer: `SELECT * FROM event e WHERE e.type = 'Accident' LIMIT 15;`

## RÈGLES CRITIQUES (ERREURS FRÉQUENTES À ÉVITER):
1. **SELECT uniquement** (jamais INSERT/UPDATE/DELETE)
2. **Alias obligatoires:** e=event, p=person, r=risk, cm=corrective_measure, ou=organizational_unit
3. **Concaténation noms:** p.name || ' ' || p.family_name AS nom_complet
4. **Ordre:** ORDER BY e.start_datetime DESC pour "récents"
5. **Limite:** LIMIT 10-20 par défaut (sauf demande explicite)
6. **Joins:** LEFT JOIN pour inclure NULL, INNER JOIN pour exclure
7. **Tables liaison:** event_employee, event_risk, event_corrective_measure
8. **AGRÉGATS:** Si COUNT/SUM/AVG/MAX/MIN alors GROUP BY OBLIGATOIRE
9. **Colonnes SELECT:** Toutes les colonnes du SELECT doivent être dans GROUP BY OU être agrégées
10. **DATES:** Utilise CAST(start_datetime AS DATE) ou TO_CHAR() pour formater
11. **NOMS DE COLONNES:** Utilise TOUJOURS les alias de table (e.event_id, pas juste event_id)
12. **WHERE vs HAVING:** WHERE avant GROUP BY, HAVING après GROUP BY
13. **Guillemets:** Utilise ' pour les chaînes, pas "
14. **NULL:** Utilise IS NULL ou IS NOT NULL (jamais = NULL)
15. **Parenthèses:** Vérifie l'équilibre dans les conditions complexes

## QUESTION DE L'UTILISATEUR:
{question}

## RÉPONDS AVEC:
1. La requête SQL (entre [SQL_START] et [SQL_END])
2. Une brève explication (entre [EXPLAIN_START] et [EXPLAIN_END])

Format de réponse:
[SQL_START]
<requête SQL ici - BIEN FORMATÉE, SANS ERREUR DE SYNTAXE>
[SQL_END]

[EXPLAIN_START]
<explication courte de ce que fait la requête>
[EXPLAIN_END]

**IMPORTANT:** La requête SQL DOIT être exécutable telle quelle, sans modification.
"""
        
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text
            
            # Extraction du SQL
            sql_match = re.search(r'\[SQL_START\](.*?)\[SQL_END\]', response_text, re.DOTALL)
            explain_match = re.search(r'\[EXPLAIN_START\](.*?)\[EXPLAIN_END\]', response_text, re.DOTALL)
            
            if sql_match:
                sql = sql_match.group(1).strip()
                # Nettoyer le SQL (enlever les balises markdown si présentes)
                sql = re.sub(r'^```sql\s*', '', sql)
                sql = re.sub(r'^```\s*', '', sql)
                sql = re.sub(r'\s*```$', '', sql)
                sql = sql.strip()
                
                # Validation et nettoyage supplémentaire du SQL
                sql = self._clean_and_validate_sql(sql)
                
                explanation = explain_match.group(1).strip() if explain_match else "Requête générée"
                
                return {
                    'success': True,
                    'sql': sql,
                    'explanation': explanation,
                    'raw_response': response_text
                }
            else:
                # Si pas de balises, essayer d'extraire du code SQL
                sql_code = re.search(r'```sql\s*(.*?)\s*```', response_text, re.DOTALL)
                if sql_code:
                    sql = sql_code.group(1).strip()
                    return {
                        'success': True,
                        'sql': sql,
                        'explanation': "Requête générée à partir du code",
                        'raw_response': response_text
                    }
                
                return {
                    'success': False,
                    'error': "Impossible d'extraire la requête SQL de la réponse",
                    'raw_response': response_text
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f"Erreur lors de la génération SQL: {str(e)}"
            }
    
    def _clean_and_validate_sql(self, sql: str) -> str:
        """
        Nettoie et valide le SQL pour éviter les erreurs de syntaxe.
        """
        # Enlever les espaces multiples mais GARDER les retours à la ligne pour lisibilité
        sql = re.sub(r'[ \t]+', ' ', sql)  # Espaces/tabs multiples -> 1 espace
        sql = re.sub(r'\n\s*\n', '\n', sql)  # Lignes vides multiples -> 1 ligne
        
        # Vérifier l'équilibre des parenthèses
        if sql.count('(') != sql.count(')'):
            raise ValueError(f"Parenthèses non équilibrées: {sql.count('(')} ouvrantes, {sql.count(')')} fermantes")
        
        # Vérifier l'équilibre des guillemets simples
        if sql.count("'") % 2 != 0:
            raise ValueError("Guillemets simples non équilibrés")
        
        # Supprimer les points-virgules finaux multiples
        sql = re.sub(r';+$', ';', sql.strip())
        
        # S'assurer qu'il y a un point-virgule final
        if not sql.endswith(';'):
            sql += ';'
        
        return sql.strip()
    
    def format_sql_pretty(self, sql: str) -> str:
        """
        Formate le SQL de manière lisible pour le debug.
        """
        # Ajouter des retours à la ligne après les mots-clés principaux
        keywords = ['SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'INNER JOIN', 
                   'ORDER BY', 'GROUP BY', 'HAVING', 'LIMIT']
        
        formatted = sql
        for keyword in keywords:
            # Chercher le mot-clé (case insensitive)
            pattern = re.compile(r'\b' + keyword + r'\b', re.IGNORECASE)
            formatted = pattern.sub('\n' + keyword, formatted)
        
        # Nettoyer les lignes
        lines = formatted.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def validate_sql_safety(self, sql: str) -> bool:
        """
        Valide que la requête SQL est sûre (uniquement SELECT).
        """
        sql_upper = sql.upper().strip()
        
        # Vérifier qu'il n'y a pas d'opérations dangereuses
        dangerous_keywords = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE', 'GRANT', 'REVOKE']
        
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return False
        
        # Vérifier que c'est bien un SELECT
        if not sql_upper.startswith('SELECT') and not sql_upper.startswith('WITH'):
            return False
        
        return True


# Instance globale
sql_generator = SQLGenerator()
