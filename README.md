# 🛡️ Neuils-de-UTBM - Chatbot RAG Intelligent

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.12-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Assistant Expert en Gestion d'Événements, Risques et Mesures Correctives**

Un chatbot conversationnel intelligent utilisant RAG (Retrieval-Augmented Generation) pour interroger une base de données PostgreSQL de manière naturelle, comme si vous parliez à un collègue expert.

## ✨ Fonctionnalités Principales

- 🧠 **Génération Automatique de SQL** - Posez vos questions en langage naturel
- 💬 **Interface Conversationnelle** - Ton humain, réponses structurées  
- 🔍 **Transparence Totale** - SQL généré visible, données vérifiables
- 🛡️ **Sécurité Robuste** - Anti-injection SQL, validation automatique
- 📊 **Analyse Complète** - Événements, risques, mesures, personnes
- 🚀 **Déploiement Simple** - Docker tout-en-un

## 🎯 Ce que Vous Pouvez Faire

### Poser des Questions en Langage Naturel

```
"Quels sont les événements récents ?"
"Liste les risques de gravité élevée"
"Qui sont les personnes impliquées dans l'événement 5 ?"
"Quel est le coût total des mesures correctives ?"
```

Le chatbot comprend votre question, génère automatiquement le SQL approprié et vous répond de manière claire et structurée.

## 🚀 Installation Rapide (3 Étapes)

### Prérequis
- **Docker** et **Docker Compose** installés ([Docker Desktop](https://www.docker.com/products/docker-desktop/))
- **Clé API Google Gemini** ([Obtenir ici](https://makersuite.google.com/app/apikey))

### Étapes

#### 1️⃣ Configuration de la Clé API
```bash
cd backend/app
cp .env.example .env
nano .env  # ou vim, code, etc.
```

Ajoutez votre clé API :
```env
GEMINI_API_KEY=votre_clé_api_ici
```

#### 2️⃣ Démarrage des Services
```bash
cd ../..
docker-compose up -d
```

#### 3️⃣ Accès au Chatbot
Ouvrez votre navigateur sur : **http://localhost:8501**

**C'est tout ! 🎉**

## 📊 Services Disponibles

| Service | URL | Description |
|---------|-----|-------------|
| **🤖 Chatbot** | http://localhost:8501 | Interface conversationnelle Streamlit |
| **🔧 API** | http://localhost:8000 | Backend FastAPI REST |
| **📖 API Docs** | http://localhost:8000/docs | Documentation Swagger interactive |
| **💾 PostgreSQL** | localhost:5432 | Base de données |

## 💡 Exemples de Questions

### Questions Simples
- "Quels sont les événements récents ?"
- "Liste les risques identifiés"
- "Combien d'événements sont enregistrés ?"

### Questions avec Relations (JOINs automatiques)
- "Qui sont les personnes impliquées dans l'événement 5 ?"
- "Quels événements ont des risques critiques associés ?"
- "Liste les mesures correctives avec leur responsable"

### Questions Analytiques
- "Quel est le coût total des mesures correctives ?"
- "Combien d'événements par type ?"
- "Quelle unité a le plus d'événements ?"

## 🧠 Comment ça Marche ?

### Architecture RAG Intelligente

```
Question → SQL Generator → PostgreSQL → Data Retriever → Gemini LLM → Réponse
```

1. **Vous posez une question** en langage naturel
2. **Gemini génère du SQL** adapté à votre question
3. **Le système récupère les données** de PostgreSQL
4. **Gemini analyse et structure** une réponse claire
5. **Vous recevez une réponse conversationnelle** avec tableaux et détails

### 🔍 Transparence Totale

À chaque réponse, vous pouvez :
- ✅ Voir le SQL généré automatiquement
- ✅ Consulter les données brutes récupérées
- ✅ Comprendre la logique de la requête

## 🛡️ Sécurité

- ✅ Anti-injection SQL automatique
- ✅ Seules les requêtes SELECT autorisées
- ✅ Validation de toutes les requêtes
- ✅ Limitation des résultats (max 50)

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICK_START.md](QUICK_START.md) | Guide de démarrage rapide |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Vue d'ensemble complète |
| [INTELLIGENT_RAG_SYSTEM.md](INTELLIGENT_RAG_SYSTEM.md) | Architecture RAG détaillée |
| [CONVERSATIONAL_UPDATE.md](CONVERSATIONAL_UPDATE.md) | Fonctionnalités conversationnelles |
| [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Checklist de déploiement |
| [CHATBOT_README.md](CHATBOT_README.md) | Documentation technique complète |

## 🧪 Tests

### Test Rapide du Système
```bash
./test_system.sh
```

### Tests Individuels
```bash
# Test complet du RAG + SQL
docker exec -it rag_streamlit python /app/test_sql_rag.py

# Test de la récupération de données
docker exec -it rag_streamlit python /app/test_data_retriever.py
```

## ⚙️ Commandes Docker Utiles

-   **Pour démarrer l'environnement :**
    ```bash
    docker compose up
    ```

-   **Pour arrêter et supprimer les conteneurs :**
    ```bash
    docker compose down
    ```

-   **Pour forcer une réinitialisation de la base de données :**
    Si vous voulez que le script de restauration de la base de données s'exécute à nouveau, vous devez supprimer le volume de données. **Attention, cela efface toutes les données de la DB.**
    ```bash
    docker compose down -v
    ```

-   **Pour voir les logs d'un service en particulier (très utile pour le débogage) :**
    ```bash
    # Pour voir les logs de la base de données
    docker compose logs -f rag_db

    # Pour voir les logs du backend
    docker compose logs -f rag_backend
    ```

## 📂 Structure du Projet

neuils-de-utbm/
├── backend/
│ ├── app/
│ │ └── main.py # Le code de notre API FastAPI
│ ├── requirements.txt # Les librairies Python
│ └── Dockerfile # Les instructions pour construire le backend
│
├── db_backup/
│ ├── 01-restore.sh # Le script qui restaure la sauvegarde
│ └── events.backup # Le fichier de sauvegarde de la base de données
│
├── docker-compose.yml # Le fichier qui orchestre tout
└── README.md # Ce fichier

## 🎉 Conclusion

**Neuils-de-UTBM** est votre assistant intelligent pour la gestion d'événements, risques et mesures correctives.

### Points Forts
- ✅ **Interface conversationnelle** - Parlez naturellement
- ✅ **SQL automatique** - Aucune compétence technique requise
- ✅ **Transparence totale** - Comprenez chaque réponse
- ✅ **Déploiement simple** - 3 étapes pour démarrer
- ✅ **Documentation complète** - 10+ guides détaillés

### Démarrage Rapide
1. Configurez `.env` avec votre clé Gemini API
2. Lancez `docker-compose up -d`
3. Ouvrez http://localhost:8501
4. Posez vos questions !

**Prêt à l'emploi. Intelligent. Conversationnel.** 🚀

---

## 📞 Support & Documentation

Pour plus d'informations, consultez :
- [Guide de Démarrage Rapide](QUICK_START.md)
- [Vue d'Ensemble du Projet](PROJECT_OVERVIEW.md)
- [Documentation Complète](CHATBOT_README.md)

---

*Développé pour le Hackathon CiT 2025 - UTBM*