# Dockerfile pour l'API FastAPI
FROM python:3.12-slim

WORKDIR /app

# Copier les dépendances et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code de l'API
COPY . /app

# Exposer le port API
EXPOSE 8000

# Lancer l'API FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
