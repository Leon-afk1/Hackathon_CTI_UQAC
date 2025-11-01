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