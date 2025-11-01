# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Utilisation de SQLite avec la base de données events.db
SQLALCHEMY_DATABASE_URL = "sqlite:///events.db"
# # Pour PostgreSQL, utilisez la ligne suivante à la place
# dbname=os.environ.get("POSTGRES_DB"),
# user=os.environ.get("POSTGRES_USER"),
# password=os.environ.get("POSTGRES_PASSWORD")
# SQLALCHEMY_DATABASE_URL = f"postgresql://{user}:{password}@localhost:5432/{dbname}"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Nécessaire pour SQLite a enlever pour PostgreSQL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()