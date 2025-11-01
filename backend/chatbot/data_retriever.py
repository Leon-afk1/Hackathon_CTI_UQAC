# data_retriever.py
"""
Module pour récupérer des données de la base de données PostgreSQL
et les formater pour le contexte RAG du LLM.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from database import SessionLocal
import models
from sql_generator import sql_generator
import traceback


class DataRetriever:
    """Classe pour récupérer et formater les données de la DB."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.sql_gen = sql_generator
    
    def __del__(self):
        """Ferme la connexion à la DB."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_database_schema(self) -> str:
        """Retourne une description du schéma de la base de données."""
        schema = """
        ## Schéma de la base de données:
        
        ### Table: person
        - person_id (Integer, PK)
        - matricule (String)
        - name (String)
        - family_name (String)
        - role (String)
        
        ### Table: organizational_unit
        - unit_id (Integer, PK)
        - identifier (String)
        - name (String)
        - location (String)
        
        ### Table: event
        - event_id (Integer, PK)
        - declared_by_id (Integer, FK -> person)
        - description (Text)
        - start_datetime (Text)
        - end_datetime (Text)
        - organizational_unit_id (Integer, FK -> organizational_unit)
        - type (String)
        - classification (String)
        
        ### Table: risk
        - risk_id (Integer, PK)
        - name (String)
        - gravity (String)
        - probability (String)
        
        ### Table: corrective_measure
        - measure_id (Integer, PK)
        - name (String)
        - description (Text)
        - owner_id (Integer, FK -> person)
        - implementation_date (Text)
        - cost (Float)
        - organizational_unit_id (Integer, FK -> organizational_unit)
        
        ### Table: event_employee (liaison)
        - event_id (FK -> event)
        - person_id (FK -> person)
        
        ### Table: event_risk (liaison)
        - event_id (FK -> event)
        - risk_id (FK -> risk)
        
        ### Table: event_corrective_measure (liaison)
        - event_id (FK -> event)
        - measure_id (FK -> corrective_measure)
        """
        return schema
    
    def search_relevant_data(self, query: str, conversation_history: list = None) -> dict:
        """
        Recherche les données pertinentes dans la DB en fonction de la requête.
        Utilise le SQL Generator pour traduire la question en SQL.
        Système de retry automatique en cas d'erreur SQL.
        
        Args:
            query: Question en langage naturel
            conversation_history: Liste des 5 derniers échanges [{question, sql, result}]
        
        Returns:
            dict avec 'context' (str), 'sql_used' (str), 'success' (bool)
        """
        max_retries = 5  # Maximum 5 tentatives avant d'abandonner
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Construire le contexte d'erreur pour les retries
                error_context = ""
                if attempt > 0 and last_error:
                    error_context = f"\n\n**ERREUR PRÉCÉDENTE (tentative {attempt}):**\n{last_error}\n\n**CORRIGE cette erreur dans ta nouvelle requête.**"
                
                # Étape 1: Générer la requête SQL à partir de la question
                sql_result = self.sql_gen.generate_sql_query(query + error_context, conversation_history)
                
                if not sql_result['success']:
                    if attempt == max_retries - 1:
                        # Dernier essai échoué, fallback
                        return {
                            'context': self._fallback_search(query),
                            'sql_used': None,
                            'explanation': "Recherche basique (génération SQL échouée)",
                            'success': False,
                            'error': sql_result.get('error', 'Erreur inconnue'),
                            'attempts': attempt + 1
                        }
                    continue
                
                sql_query = sql_result['sql']
                explanation = sql_result['explanation']
                
                # Formater le SQL pour l'affichage
                sql_formatted = self.sql_gen.format_sql_pretty(sql_query)
                
                # Étape 2: Valider la sécurité de la requête
                if not self.sql_gen.validate_sql_safety(sql_query):
                    return {
                        'context': "⚠️ Requête SQL non autorisée (sécurité)",
                        'sql_used': sql_formatted,
                        'sql_raw': sql_query,
                        'explanation': explanation,
                        'success': False,
                        'error': "Requête SQL potentiellement dangereuse",
                        'attempts': attempt + 1
                    }
                
                # Étape 3: Exécuter la requête SQL
                print(f"\n🔍 DEBUG - Tentative {attempt + 1}/{max_retries}")
                print(f"📝 SQL à exécuter:\n{sql_query}\n")
                
                result = self.db.execute(text(sql_query))
                rows = result.fetchall()
                
                print(f"✅ Requête réussie - {len(rows)} résultat(s)\n")
                
                # Étape 4: Formater les résultats
                if not rows:
                    return {
                        'context': "Aucun résultat trouvé pour cette requête.",
                        'sql_used': sql_formatted,
                        'sql_raw': sql_query,
                        'explanation': explanation,
                        'success': True,
                        'row_count': 0,
                        'attempts': attempt + 1
                    }
                
                # Formater les résultats en texte structuré
                context_lines = [f"## Résultats de la requête ({len(rows)} ligne(s)):\n"]
                
                # Récupérer les noms de colonnes
                if hasattr(result, 'keys'):
                    columns = result.keys()
                else:
                    columns = [f"col_{i}" for i in range(len(rows[0]))]
                
                # Formater chaque ligne
                for i, row in enumerate(rows[:50], 1):  # Limiter à 50 résultats max
                    context_lines.append(f"### Résultat {i}:")
                    row_dict = dict(zip(columns, row))
                    for key, value in row_dict.items():
                        if value is not None:
                            context_lines.append(f"  - {key}: {value}")
                    context_lines.append("")
                
                if len(rows) > 50:
                    context_lines.append(f"\n⚠️ {len(rows) - 50} résultats supplémentaires non affichés.")
                
                # Succès ! Retourner les résultats
                return {
                    'context': "\n".join(context_lines),
                    'sql_used': sql_formatted,
                    'sql_raw': sql_query,
                    'explanation': explanation,
                    'success': True,
                    'row_count': len(rows),
                    'attempts': attempt + 1
                }
                
            except Exception as e:
                # Enregistrer l'erreur pour le prochain essai
                last_error = f"{type(e).__name__}: {str(e)}"
                
                print(f"❌ ERREUR Tentative {attempt + 1}: {last_error}")
                if 'sql_query' in locals():
                    print(f"📝 SQL qui a échoué:\n{sql_query}\n")
                
                # Si c'est le dernier essai, retourner l'erreur
                if attempt == max_retries - 1:
                    error_trace = traceback.format_exc()
                    return {
                        'context': f"❌ Erreur lors de l'exécution de la requête (après {max_retries} tentatives):\n{str(e)}",
                        'sql_used': self.sql_gen.format_sql_pretty(sql_result.get('sql', '')) if 'sql_result' in locals() else None,
                        'sql_raw': sql_result.get('sql') if 'sql_result' in locals() else None,
                        'explanation': sql_result.get('explanation') if 'sql_result' in locals() else None,
                        'success': False,
                        'error': str(e),
                        'traceback': error_trace,
                        'attempts': attempt + 1
                    }
                # Sinon, continuer la boucle pour retry
                continue
        
        # Si on arrive ici, tous les essais ont échoué
        return {
            'context': self._fallback_search(query),
            'sql_used': None,
            'explanation': f"Recherche basique (tous les {max_retries} essais SQL ont échoué)",
            'success': False,
            'error': f"Échec après {max_retries} tentatives - Impossible de générer une requête SQL valide",
            'attempts': max_retries
        }
    
    def _fallback_search(self, query: str) -> str:
        """
        Méthode de recherche basique (fallback) si la génération SQL échoue.
        """
        context = []
        query_lower = query.lower()
        
        try:
            # Recherche dans les événements
            if any(word in query_lower for word in ['événement', 'event', 'incident', 'accident', 'récent']):
                events = self.db.query(models.Event).limit(10).all()
                if events:
                    context.append("### Événements récents:")
                    for event in events:
                        context.append(f"- ID {event.event_id}: {event.description} "
                                     f"(Type: {event.type}, Classification: {event.classification})")
            
            # Recherche dans les risques
            if any(word in query_lower for word in ['risque', 'risk', 'danger', 'gravité']):
                risks = self.db.query(models.Risk).limit(10).all()
                if risks:
                    context.append("\n### Risques identifiés:")
                    for risk in risks:
                        context.append(f"- {risk.name} (Gravité: {risk.gravity}, "
                                     f"Probabilité: {risk.probability})")
            
            # Recherche dans les mesures correctives
            if any(word in query_lower for word in ['mesure', 'correction', 'action', 'prévention']):
                measures = self.db.query(models.CorrectiveMeasure).limit(10).all()
                if measures:
                    context.append("\n### Mesures correctives:")
                    for measure in measures:
                        context.append(f"- {measure.name}: {measure.description} "
                                     f"(Coût: {measure.cost if measure.cost else 'N/A'})")
            
            # Recherche dans les personnes
            if any(word in query_lower for word in ['personne', 'employé', 'responsable', 'auteur', 'impliqué']):
                persons = self.db.query(models.Person).limit(10).all()
                if persons:
                    context.append("\n### Personnes:")
                    for person in persons:
                        context.append(f"- {person.name} {person.family_name} "
                                     f"(Matricule: {person.matricule}, Rôle: {person.role})")
            
            # Si aucune donnée pertinente n'a été trouvée, on récupère un aperçu général
            if not context:
                context.append("### Aperçu général de la base de données:")
                event_count = self.db.query(models.Event).count()
                risk_count = self.db.query(models.Risk).count()
                measure_count = self.db.query(models.CorrectiveMeasure).count()
                person_count = self.db.query(models.Person).count()
                
                context.append(f"- Nombre d'événements: {event_count}")
                context.append(f"- Nombre de risques: {risk_count}")
                context.append(f"- Nombre de mesures correctives: {measure_count}")
                context.append(f"- Nombre de personnes: {person_count}")
        
        except Exception as e:
            context.append(f"Erreur lors de la récupération des données: {str(e)}")
        
        return "\n".join(context) if context else "Aucune donnée pertinente trouvée."
    
    def execute_custom_query(self, sql_query: str) -> str:
        """
        Exécute une requête SQL personnalisée (à utiliser avec précaution).
        """
        try:
            result = self.db.execute(text(sql_query))
            rows = result.fetchall()
            
            if not rows:
                return "Aucun résultat trouvé."
            
            # Formatage des résultats
            output = []
            for row in rows:
                output.append(str(dict(row._mapping)))
            
            return "\n".join(output)
        except Exception as e:
            return f"Erreur lors de l'exécution de la requête: {str(e)}"


# Instance globale pour l'import
data_retriever = DataRetriever()
