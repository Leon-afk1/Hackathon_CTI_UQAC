# Dockerfile pour le Chatbot Streamlit
FROM python:3.12-slim

WORKDIR /app

# Copier les dépendances et installer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code du chatbot
COPY . /app

# Exposer le port Streamlit
EXPOSE 8501

# Lancer Streamlit
CMD ["streamlit", "run", "chatbot_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
