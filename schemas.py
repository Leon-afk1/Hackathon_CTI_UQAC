# schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional

# Schéma pour Event
class EventBase(BaseModel):
    declared_by_id: int
    description: str
    start_datetime: str
    end_datetime: Optional[str] = None
    organizational_unit_id: int
    type: str
    classification: str

class Event(EventBase):
    event_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Schéma pour Person
class PersonBase(BaseModel):
    matricule: str
    name: str
    family_name: str
    role: str

class Person(PersonBase):
    person_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Schéma pour OrganizationalUnit
class OrganizationalUnitBase(BaseModel):
    identifier: str
    name: str
    location: str

class OrganizationalUnit(OrganizationalUnitBase):
    unit_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Schéma pour CorrectiveMeasure
class CorrectiveMeasureBase(BaseModel):
    name: str
    description: str
    owner_id: int
    implementation_date: str
    cost: Optional[float] = None
    organizational_unit_id: int

class CorrectiveMeasure(CorrectiveMeasureBase):
    measure_id: int
    
    model_config = ConfigDict(from_attributes=True)

# Schéma pour Risk
class RiskBase(BaseModel):
    name: str
    gravity: str
    probability: str

class Risk(RiskBase):
    risk_id: int
    
    model_config = ConfigDict(from_attributes=True)