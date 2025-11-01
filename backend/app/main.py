# main.py
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

import models, schemas
from database import SessionLocal, engine

app = FastAPI(title="Events Safety API", version="1.0.0")

# Dépendance pour obtenir une session de DB par requête
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === ENDPOINTS POUR LES EVENTS ===
@app.get("/events/", response_model=List[schemas.Event])
def read_events(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Récupère une liste d'événements."""
    events = db.query(models.Event).offset(skip).limit(limit).all()
    return events

@app.get("/events/{event_id}", response_model=schemas.Event)
def read_event(event_id: int, db: Session = Depends(get_db)):
    """Récupère un événement par son identifiant."""
    event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    return event

@app.post("/events/", response_model=schemas.Event, status_code=201)
def create_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    """Crée un nouvel événement."""
    db_event = models.Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

@app.put("/events/{event_id}", response_model=schemas.Event)
def update_event(event_id: int, event: schemas.EventUpdate, db: Session = Depends(get_db)):
    """Met à jour un événement existant."""
    db_event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    for key, value in event.model_dump(exclude_unset=True).items():
        setattr(db_event, key, value)
    
    db.commit()
    db.refresh(db_event)
    return db_event

@app.delete("/events/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Supprime un événement."""
    db_event = db.query(models.Event).filter(models.Event.event_id == event_id).first()
    if db_event is None:
        raise HTTPException(status_code=404, detail="Événement non trouvé")
    
    db.delete(db_event)
    db.commit()
    return None

# === ENDPOINTS POUR LES PERSONS ===
@app.get("/persons/", response_model=List[schemas.Person])
def read_persons(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Récupère une liste de personnes."""
    persons = db.query(models.Person).offset(skip).limit(limit).all()
    return persons

@app.get("/persons/{person_id}", response_model=schemas.Person)
def read_person(person_id: int, db: Session = Depends(get_db)):
    """Récupère une personne par son identifiant."""
    person = db.query(models.Person).filter(models.Person.person_id == person_id).first()
    if person is None:
        raise HTTPException(status_code=404, detail="Personne non trouvée")
    return person

@app.post("/persons/", response_model=schemas.Person, status_code=201)
def create_person(person: schemas.PersonCreate, db: Session = Depends(get_db)):
    """Crée une nouvelle personne."""
    db_person = models.Person(**person.model_dump())
    db.add(db_person)
    db.commit()
    db.refresh(db_person)
    return db_person

@app.put("/persons/{person_id}", response_model=schemas.Person)
def update_person(person_id: int, person: schemas.PersonUpdate, db: Session = Depends(get_db)):
    """Met à jour une personne existante."""
    db_person = db.query(models.Person).filter(models.Person.person_id == person_id).first()
    if db_person is None:
        raise HTTPException(status_code=404, detail="Personne non trouvée")
    
    for key, value in person.model_dump(exclude_unset=True).items():
        setattr(db_person, key, value)
    
    db.commit()
    db.refresh(db_person)
    return db_person

@app.delete("/persons/{person_id}", status_code=204)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    """Supprime une personne."""
    db_person = db.query(models.Person).filter(models.Person.person_id == person_id).first()
    if db_person is None:
        raise HTTPException(status_code=404, detail="Personne non trouvée")
    
    db.delete(db_person)
    db.commit()
    return None

# === ENDPOINTS POUR LES ORGANIZATIONAL UNITS ===
@app.get("/units/", response_model=List[schemas.OrganizationalUnit])
def read_units(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Récupère toutes les unités organisationnelles."""
    units = db.query(models.OrganizationalUnit).offset(skip).limit(limit).all()
    return units

@app.get("/units/{unit_id}", response_model=schemas.OrganizationalUnit)
def read_unit(unit_id: int, db: Session = Depends(get_db)):
    """Récupère une unité organisationnelle par son identifiant."""
    unit = db.query(models.OrganizationalUnit).filter(models.OrganizationalUnit.unit_id == unit_id).first()
    if unit is None:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    return unit

@app.post("/units/", response_model=schemas.OrganizationalUnit, status_code=201)
def create_unit(unit: schemas.OrganizationalUnitCreate, db: Session = Depends(get_db)):
    """Crée une nouvelle unité organisationnelle."""
    db_unit = models.OrganizationalUnit(**unit.model_dump())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.put("/units/{unit_id}", response_model=schemas.OrganizationalUnit)
def update_unit(unit_id: int, unit: schemas.OrganizationalUnitUpdate, db: Session = Depends(get_db)):
    """Met à jour une unité organisationnelle existante."""
    db_unit = db.query(models.OrganizationalUnit).filter(models.OrganizationalUnit.unit_id == unit_id).first()
    if db_unit is None:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    for key, value in unit.model_dump(exclude_unset=True).items():
        setattr(db_unit, key, value)
    
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.delete("/units/{unit_id}", status_code=204)
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    """Supprime une unité organisationnelle."""
    db_unit = db.query(models.OrganizationalUnit).filter(models.OrganizationalUnit.unit_id == unit_id).first()
    if db_unit is None:
        raise HTTPException(status_code=404, detail="Unité organisationnelle non trouvée")
    
    db.delete(db_unit)
    db.commit()
    return None

# === ENDPOINTS POUR LES CORRECTIVE MEASURES ===
@app.get("/measures/", response_model=List[schemas.CorrectiveMeasure])
def read_measures(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Récupère une liste de mesures correctives."""
    measures = db.query(models.CorrectiveMeasure).offset(skip).limit(limit).all()
    return measures

@app.get("/measures/{measure_id}", response_model=schemas.CorrectiveMeasure)
def read_measure(measure_id: int, db: Session = Depends(get_db)):
    """Récupère une mesure corrective par son identifiant."""
    measure = db.query(models.CorrectiveMeasure).filter(models.CorrectiveMeasure.measure_id == measure_id).first()
    if measure is None:
        raise HTTPException(status_code=404, detail="Mesure corrective non trouvée")
    return measure

@app.post("/measures/", response_model=schemas.CorrectiveMeasure, status_code=201)
def create_measure(measure: schemas.CorrectiveMeasureCreate, db: Session = Depends(get_db)):
    """Crée une nouvelle mesure corrective."""
    db_measure = models.CorrectiveMeasure(**measure.model_dump())
    db.add(db_measure)
    db.commit()
    db.refresh(db_measure)
    return db_measure

@app.put("/measures/{measure_id}", response_model=schemas.CorrectiveMeasure)
def update_measure(measure_id: int, measure: schemas.CorrectiveMeasureUpdate, db: Session = Depends(get_db)):
    """Met à jour une mesure corrective existante."""
    db_measure = db.query(models.CorrectiveMeasure).filter(models.CorrectiveMeasure.measure_id == measure_id).first()
    if db_measure is None:
        raise HTTPException(status_code=404, detail="Mesure corrective non trouvée")
    
    for key, value in measure.model_dump(exclude_unset=True).items():
        setattr(db_measure, key, value)
    
    db.commit()
    db.refresh(db_measure)
    return db_measure

@app.delete("/measures/{measure_id}", status_code=204)
def delete_measure(measure_id: int, db: Session = Depends(get_db)):
    """Supprime une mesure corrective."""
    db_measure = db.query(models.CorrectiveMeasure).filter(models.CorrectiveMeasure.measure_id == measure_id).first()
    if db_measure is None:
        raise HTTPException(status_code=404, detail="Mesure corrective non trouvée")
    
    db.delete(db_measure)
    db.commit()
    return None

# === ENDPOINTS POUR LES RISKS ===
@app.get("/risks/", response_model=List[schemas.Risk])
def read_risks(db: Session = Depends(get_db)):
    """Récupère tous les risques."""
    risks = db.query(models.Risk).all()
    return risks

@app.get("/risks/{risk_id}", response_model=schemas.Risk)
def read_risk(risk_id: int, db: Session = Depends(get_db)):
    """Récupère un risque par son identifiant."""
    risk = db.query(models.Risk).filter(models.Risk.risk_id == risk_id).first()
    if risk is None:
        raise HTTPException(status_code=404, detail="Risque non trouvé")
    return risk

@app.post("/risks/", response_model=schemas.Risk, status_code=201)
def create_risk(risk: schemas.RiskCreate, db: Session = Depends(get_db)):
    """Crée un nouveau risque."""
    db_risk = models.Risk(**risk.model_dump())
    db.add(db_risk)
    db.commit()
    db.refresh(db_risk)
    return db_risk

@app.put("/risks/{risk_id}", response_model=schemas.Risk)
def update_risk(risk_id: int, risk: schemas.RiskUpdate, db: Session = Depends(get_db)):
    """Met à jour un risque existant."""
    db_risk = db.query(models.Risk).filter(models.Risk.risk_id == risk_id).first()
    if db_risk is None:
        raise HTTPException(status_code=404, detail="Risque non trouvé")
    
    for key, value in risk.model_dump(exclude_unset=True).items():
        setattr(db_risk, key, value)
    
    db.commit()
    db.refresh(db_risk)
    return db_risk

@app.delete("/risks/{risk_id}", status_code=204)
def delete_risk(risk_id: int, db: Session = Depends(get_db)):
    """Supprime un risque."""
    db_risk = db.query(models.Risk).filter(models.Risk.risk_id == risk_id).first()
    if db_risk is None:
        raise HTTPException(status_code=404, detail="Risque non trouvé")
    
    db.delete(db_risk)
    db.commit()
    return None

@app.get("/")
def root():
    """Page d'accueil de l'API."""
    return {
        "message": "Bienvenue sur l'API Events Safety",
        "endpoints": {
            "events": "/events/",
            "persons": "/persons/",
            "units": "/units/",
            "measures": "/measures/",
            "risks": "/risks/",
            "docs": "/docs"
        }
    }

####TEST ONLY

# import os
# import psycopg2
# from flask import Flask, jsonify
# from psycopg2.extras import RealDictCursor

# app = Flask(__name__)

# def get_db_connection():
#     """Établit une connexion à la base de données PostgreSQL."""
#     conn = psycopg2.connect(
#         host="db",  # Le nom du service de la base de données dans docker-compose
#         dbname=os.environ.get("POSTGRES_DB"),
#         user=os.environ.get("POSTGRES_USER"),
#         password=os.environ.get("POSTGRES_PASSWORD")
#     )
#     return conn

# @app.route('/')
# def index():
#     return "Le backend Python fonctionne !"

# @app.route('/test-db')
# def test_db():
#     """Teste la connexion à la base de données et récupère la version de PostgreSQL."""
#     try:
#         conn = get_db_connection()
#         cur = conn.cursor()
#         cur.execute('SELECT version()')
#         db_version = cur.fetchone()
#         cur.close()
#         conn.close()
#         return jsonify({"message": "Connexion à la base de données réussie !", "version": db_version})
#     except Exception as e:
#         return jsonify({"message": "Erreur de connexion à la base de données.", "error": str(e)}), 500

# # --- NOUVELLE ROUTE ---
# @app.route('/events')
# def get_events():
#     """Récupère les 5 premiers événements de la base de données."""
#     try:
#         conn = get_db_connection()
#         # RealDictCursor permet d'obtenir les résultats sous forme de dictionnaires (clé: valeur)
#         cur = conn.cursor(cursor_factory=RealDictCursor)
        
#         # Exécution de la requête simple
#         cur.execute('SELECT * FROM public.event ORDER BY event_id DESC LIMIT 5')
        
#         # Récupération de tous les résultats
#         events = cur.fetchall()
        
#         cur.close()
#         conn.close()
        
#         # Retourne les résultats au format JSON
#         return jsonify(events)
        
#     except Exception as e:
#         return jsonify({"message": "Erreur lors de la récupération des événements.", "error": str(e)}), 500
# # --- FIN DE LA NOUVELLE ROUTE ---

# if __name__ == '__main__':
#     app.run(host='0.0.0.0', port=5000)
