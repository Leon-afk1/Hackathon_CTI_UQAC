# database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Utilisation de SQLite avec la base de données events.db
SQLALCHEMY_DATABASE_URL = "sqlite:///events.db"
# # Pour PostgreSQL, utilisez la ligne suivante à la place
# SQLALCHEMY_DATABASE_URL = "postgresql://your_username:your_password@localhost:5432/your_database"


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}  # Nécessaire pour SQLite a enlever pour PostgreSQL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()