# models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

# Modèle pour la table event
class Event(Base):
    __tablename__ = "event"
    
    event_id = Column(Integer, primary_key=True, index=True)
    declared_by_id = Column(Integer, ForeignKey("person.person_id"))
    description = Column(Text)
    start_datetime = Column(Text)  # SQLite stocke les dates en TEXT
    end_datetime = Column(Text, nullable=True)
    organizational_unit_id = Column(Integer, ForeignKey("organizational_unit.unit_id"))
    type = Column(String)
    classification = Column(String)

# Modèle pour la table person
class Person(Base):
    __tablename__ = "person"
    
    person_id = Column(Integer, primary_key=True, index=True)
    matricule = Column(String)
    name = Column(String)
    family_name = Column(String)
    role = Column(String)

# Modèle pour la table organizational_unit
class OrganizationalUnit(Base):
    __tablename__ = "organizational_unit"
    
    unit_id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String)
    name = Column(String)
    location = Column(String)

# Modèle pour la table corrective_measure
class CorrectiveMeasure(Base):
    __tablename__ = "corrective_measure"
    
    measure_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("person.person_id"))
    implementation_date = Column(Text)
    cost = Column(Float, nullable=True)
    organizational_unit_id = Column(Integer, ForeignKey("organizational_unit.unit_id"))

# Modèle pour la table risk
class Risk(Base):
    __tablename__ = "risk"
    
    risk_id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    gravity = Column(String)
    probability = Column(String)