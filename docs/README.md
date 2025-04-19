
# **Streamotion**

Streamotion est un projet d'analyse en temps réel des émotions des utilisateurs de Reddit, utilisant Kafka pour le streaming des commentaires, Spark pour le traitement en temps réel, FastAPI pour l'analyse des émotions via un modèle NLP, et BigQuery pour le stockage des résultats. Le projet permet de visualiser les émotions des utilisateurs via un dashboard interactif avec Streamlit.

---

## 🧱 **Le projet repose sur :**

- Des pipelines de streaming en temps réel pour l'extraction, le traitement et le stockage des données.
- Kafka pour l'extraction des commentaires Reddit en temps réel.
- Spark Structured Streaming pour le traitement des données en temps réel.
- FastAPI pour héberger un modèle NLP de huggingFace pour la classification des émotions dans les textes.
- BigQuery pour le stockage des données traitées.
- Docker pour conteneuriser les différents services et garantir la portabilité.
- Streamlit pour la visualisation interactive des résultats.
- Déploiement sur une VM avec Docker, permettant une exécution continue.

---

## 🗂️ **Architecture du projet**

```bash
.
├── app
│   ├── api.py
│   ├── extract.py
│   └── trans_load.py
├── archi_docker
│   ├── dockerfile.api
│   ├── dockerfile.produceur
│   └── dockerfile.spark
├── docker-compose.yml
├── graph.py
├── main.py
├── requirements.txt
└── tests/
    ├── tests.py
```

---

## 🔄 **Pipelines**

Les pipelines suivent les bonnes pratiques d'ingénierie de données, avec un focus sur la modularité et la scalabilité. Ils sont conçus pour l'extraction, la transformation et le stockage des données en temps réel.

- **Kafka** : Extraction des commentaires Reddit via PRAW et envoi dans un topic Kafka.
- **Spark Streaming** : Traitement des commentaires Reddit en temps réel via Spark, appel à l'API FastAPI pour l'analyse des émotions, puis stockage des résultats dans BigQuery.
- **FastAPI** : API pour l'analyse des émotions des commentaires Reddit avec un modèle NLP.
- **BigQuery** : Stockage des résultats des analyses émotionnelles pour des requêtes et visualisations ultérieures.

---

## 📈 **Données et Traitement**

### **Commentaires Reddit - extract.py**

- **Source** : Reddit via l'API PRAW.
- **Données** : Extraction des commentaires Reddit en temps réel.
- **Pipeline** : Extraction → Publication dans Kafka.

### **Analyse des émotions - trans_load.py**

- **Source** : FastAPI avec un modèle NLP HuggingFace pour la classification des émotions.
- **Données** : Chaque commentaire Reddit est envoyé à l'API FastAPI pour l'analyse émotionnelle.
- **Pipeline** : Kafka → FastAPI → BigQuery.

### **Visualisation des émotions - graph.py**

- **Outil** : Streamlit pour la visualisation des émotions en temps réel.
- **Graphiques** : Visualisation dynamique des émotions des utilisateurs (joie, colère, tristesse, etc.).

---

## 🤖 **Modèle NLP - FastAPI**

Le modèle NLP est basé sur des transformers (comme BERT ou DistilBERT), et il est hébergé dans un service FastAPI pour fournir des prédictions en temps réel sur les émotions des commentaires Reddit.

- **Entrée** : Texte des commentaires Reddit.
- **Sortie** : Prédiction d'une émotion ("joy", "anger", etc.).

---

## ✅ **Objectifs pédagogiques**

- **Organisation d'un projet Data Engineering** : Structuration et organisation propre du projet.
- **Pipelines de Streaming en temps réel** : Pratique de l'ingénierie de données en temps réel avec Kafka et Spark.
- **Analyse NLP avec FastAPI** : Déploiement d'un modèle NLP pour la classification des émotions.
- **Visualisation en temps réel** : Création d'un dashboard interactif avec Streamlit pour visualiser les résultats en temps réel.
