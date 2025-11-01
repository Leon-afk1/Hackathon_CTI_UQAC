# schemas.py
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# ============ EVENT SCHEMAS ============
class EventBase(BaseModel):
    declared_by_id: int
    description: str
    start_datetime: datetime
    end_datetime: Optional[datetime] = None
    organizational_unit_id: int
    type: str
    classification: str

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    declared_by_id: Optional[int] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    organizational_unit_id: Optional[int] = None
    type: Optional[str] = None
    classification: Optional[str] = None

class Event(EventBase):
    event_id: int
    
    model_config = ConfigDict(from_attributes=True)

class EventEnriched(Event):
    """Event avec informations extraites de la description"""
    extracted_date: Optional[str] = None
    extracted_time: Optional[str] = None
    extracted_shift: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# ============ PERSON SCHEMAS ============
class PersonBase(BaseModel):
    matricule: str
    name: str
    family_name: str
    role: str

class PersonCreate(PersonBase):
    pass

class PersonUpdate(BaseModel):
    matricule: Optional[str] = None
    name: Optional[str] = None
    family_name: Optional[str] = None
    role: Optional[str] = None

class Person(PersonBase):
    person_id: int
    
    model_config = ConfigDict(from_attributes=True)

# ============ ORGANIZATIONAL UNIT SCHEMAS ============
class OrganizationalUnitBase(BaseModel):
    identifier: str
    name: str
    location: str

class OrganizationalUnitCreate(OrganizationalUnitBase):
    pass

class OrganizationalUnitUpdate(BaseModel):
    identifier: Optional[str] = None
    name: Optional[str] = None
    location: Optional[str] = None

class OrganizationalUnit(OrganizationalUnitBase):
    unit_id: int
    
    model_config = ConfigDict(from_attributes=True)

# ============ CORRECTIVE MEASURE SCHEMAS ============
class CorrectiveMeasureBase(BaseModel):
    name: str
    description: str
    owner_id: int
    implementation_date: datetime
    cost: Optional[float] = None
    organizational_unit_id: int

class CorrectiveMeasureCreate(CorrectiveMeasureBase):
    pass

class CorrectiveMeasureUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    owner_id: Optional[int] = None
    implementation_date: Optional[datetime] = None
    cost: Optional[float] = None
    organizational_unit_id: Optional[int] = None

class CorrectiveMeasure(CorrectiveMeasureBase):
    measure_id: int
    
    model_config = ConfigDict(from_attributes=True)

# ============ RISK SCHEMAS ============
class RiskBase(BaseModel):
    name: str
    gravity: str
    probability: str

class RiskCreate(RiskBase):
    pass

class RiskUpdate(BaseModel):
    name: Optional[str] = None
    gravity: Optional[str] = None
    probability: Optional[str] = None

class Risk(RiskBase):
    risk_id: int
    
    model_config = ConfigDict(from_attributes=True)