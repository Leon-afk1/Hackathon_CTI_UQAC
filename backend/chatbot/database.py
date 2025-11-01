# database.py - Configuration pour le Chatbot
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Récupération des variables d'environnement
dbname = os.environ.get("POSTGRES_DB", "madb")
user = os.environ.get("POSTGRES_USER", "monuser")
password = os.environ.get("POSTGRES_PASSWORD", "monpassword")
host = os.environ.get("POSTGRES_HOST", "db")
port = os.environ.get("POSTGRES_PORT", "5432")

# Construction de l'URL PostgreSQL
SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    # connect_args={"check_same_thread": False}  # Nécessaire pour SQLite a enlever pour PostgreSQL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()