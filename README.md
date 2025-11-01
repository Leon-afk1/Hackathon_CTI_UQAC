# Neuils-de-UTBM
https://catalog.us-east-1.prod.workshops.aws/join?access-code=f3da-1853ed-21


# Installe docker

# Projet RAG 

Ce projet fournit un environnement de développement complet et conteneurisé pour notre application RAG. Il inclut un backend en Python 3.12 et une base de données PostgreSQL qui se charge automatiquement à partir d'une sauvegarde.

Tout est géré par Docker, vous n'avez donc pas besoin d'installer Python ou PostgreSQL sur votre machine.

## Prérequis

Avant de commencer, assurez-vous d'avoir installé **Docker** sur votre machine.

-   **Pour Windows et macOS :** La méthode la plus simple est d'installer [Docker Desktop](https://www.docker.com/products/docker-desktop/).
-   **Pour Linux :** Suivez la [procédure d'installation officielle](https://docs.docker.com/engine/install/) pour votre distribution et assurez-vous d'installer également le plugin `docker-compose-plugin`.

## Installation et Lancement Rapide

1.  **Clonez le projet**
    Si ce n'est pas déjà fait, récupérez le code source.
    ```bash
    git clone <URL_de_votre_repo>
    cd neuils-de-utbm
    ```

2.  **Lancez l'environnement**
    Ouvrez un terminal à la racine du projet et exécutez la commande suivante :
    ```bash
    docker compose up --build
    ```
    -   Cette commande va construire l'image Docker de notre backend Python, télécharger l'image de PostgreSQL 18 et démarrer les deux conteneurs.
    -   La base de données sera automatiquement restaurée à partir du fichier de sauvegarde situé dans `db_backup`.
    -   La première exécution peut prendre quelques minutes, le temps de télécharger les images.

Et voilà ! L'environnement est prêt. Le backend est accessible sur le port 5000 et la base de données sur le port 5432.

##  Vérification

Pour vérifier que tout fonctionne correctement :

1.  **Vérifiez le backend :**
    Ouvrez votre navigateur et allez sur [http://localhost:5000/](http://localhost:5000/). Vous devriez voir le message :
    `Le backend Python fonctionne !`

2.  **Vérifiez la connexion à la base de données :**
    Allez sur [http://localhost:5000/events](http://localhost:5000/events). Vous devriez voir une page remplie de données au format JSON, correspondant aux 5 derniers événements de la base de données.

3.  **(Optionnel) Se connecter à la base de données :**
    Vous pouvez vous connecter à la base de données avec un client SQL (comme DBeaver, TablePlus, etc.) en utilisant les informations suivantes :
    -   **Hôte :** `localhost`
    -   **Port :** `5432`
    -   **Base de données :** `madb`
    -   **Utilisateur :** `monuser`
    -   **Mot de passe :** `monpassword`

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