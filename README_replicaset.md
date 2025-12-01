# 📌 Réplication MongoDB – ReplicaSet local (Projet NoScites)

Ce document décrit la mise en place du ReplicaSet local utilisé dans la 2ᵉ partie du projet NoScites.

---

# 1️⃣ Objectif pédagogique

L’objectif est de :

- Protéger les données contre les pannes
- Garantir la haute disponibilité
- Simuler un environnement multi-serveurs en local
- Répliquer automatiquement les données entre plusieurs nœuds

Ce ReplicaSet servait uniquement pour la partie "réplication" du projet.  
La partie sharding (3ᵉ étape) utilise une autre architecture.

---

# 2️⃣ Architecture utilisée

           ┌────────────────────────────────────────────┐
           │                 ReplicaSet rs0             │
           └────────────────────────────────────────────┘

 ┌───────────────┐     ┌────────────────┐      ┌────────────────┐
 │   PRIMARY     │     │   SECONDARY    │      │    ARBITER     │
 │ port 27021    │     │ port 27022     │      │ port 27023     │
 │ rs01 data path│     │ rs02 data path │      │ rs03 data path │
 └───────────────┘     └────────────────┘      └────────────────┘

📁 **Chemins exacts sur ma machine :**


C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\rs01
C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\rs02
C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\rs03


---

# 3️⃣ Démarrage complet après extinction du PC

## ➤ Étape 1 : démarrer les 3 instances mongod

```
mongod --port 27021 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\rs01 --replSet rs0
mongod --port 27022 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\rs02 --replSet rs0
mongod --port 27023 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\rs03 --replSet rs0 --arbiterOnly
```
⚠️ Laisser les 3 fenêtres ouvertes.

4️⃣ Initialisation du ReplicaSet (à faire uniquement la 1ère fois)

Se connecter au PRIMARY et initialiser :
```
mongosh --port 27021
rs.initiate({
  _id: "rs0",
  members: [
    { _id: 0, host: "localhost:27021" },
    { _id: 1, host: "localhost:27022" },
    { _id: 2, host: "localhost:27023", arbiterOnly: true }
  ]
})
```

5️⃣ Vérification

Toujours dans mongosh :
rs.status()

Tu dois voir :

PRIMARY : 27021
SECONDARY : 27022
ARBITER : 27023

6️⃣ Ingestion des données avec Docker
```
docker compose run --rm ingest_nested
```
Le script détecte Paris / Lyon et ajoute city.

7️⃣ Vérification dans mongosh
```
mongosh --port 27021

use noscites
db.listings_nested.countDocuments()
db.listings_nested.countDocuments({ city: "Paris" })
db.listings_nested.countDocuments({ city: "Lyon" })

```
8️⃣ Accès via MongoDB Compass

URL à utiliser dans le compose pour voir le ReplicaSet :
```
mongodb://localhost:27021,localhost:27022,localhost:27023/?replicaSet=rs0


```