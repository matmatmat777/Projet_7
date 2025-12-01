# 📌 Distribution des données MongoDB – Sharding (Projet NoScites)

Ce document décrit **toute la mise en place du cluster sharding** local utilisé pour la 3ᵉ partie du projet NoScites.

---

# 1️⃣ Objectif pédagogique

Le but du sharding :

- Distribuer les données sur plusieurs serveurs
- Optimiser les performances
- Permettre des requêtes rapides selon le site (Paris / Lyon)
- Gérer une montée en charge

---

# 2️⃣ Architecture finale (sharding complet)

                  ┌──────────────────────────┐
                  │        mongos router     │
                  │        port 27017        │
                  └──────────────┬───────────┘
                                 │
                                 ▼
               ┌──────────────────────────────────────┐
               │           CONFIG REPLICA SET         │
               │   configReplSet (27040–27042)        │
               └──────────────────────────────────────┘
                     │                        │
     ┌───────────────┘                        └────────────────┐
     ▼                                                         ▼
┌─────────────────────┐                     ┌──────────────────────┐
│ Shard PARIS         │                     │ Shard LYON           │
│ ReplicaSet rsParis  │                     │ ReplicaSet rsLyon    │
│ mongod : 27041      │                     │ mongod : 27042       │
└─────────────────────┘                     └──────────────────────┘    

Chaque shard contient les documents d’une ville grâce au shard key : { city : 1 }


---

# 3️⃣ Dossier de stockage (sur ton PC)

C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\config
C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\paris
C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\lyon


---

# 4️⃣ Démarrage complet du cluster (après extinction du PC)

## ➤ 1. Démarrer les CONFIG SERVERS (ReplicaSet)

```powershell
mongod --configsvr --replSet configReplSet --port 27040 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\config

mongod --configsvr --replSet configReplSet --port 27041 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\config

mongod --configsvr --replSet configReplSet --port 27042 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\config

Initialisation :
mongosh --port 27040

rs.initiate({
  _id: "configReplSet",
  configsvr: true,
  members: [
    { _id: 0, host: "localhost:27040" },
    { _id: 1, host: "localhost:27041" },
    { _id: 2, host: "localhost:27042" }
  ]
})

➤ 2. Démarrer les SHARDS
Shard PARIS
mongod --shardsvr --replSet rsParis --port 27041 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\paris

Initialisation :
mongosh --port 27041

rs.initiate({
  _id: "rsParis",
  members: [ { _id: 0, host: "localhost:27041" } ]
})

Shard LYON
mongod --shardsvr --replSet rsLyon --port 27042 --dbpath C:\Users\matde\Documents\OpenClassrooms\Projet_7\data\lyon

Initialisation :
mongosh --port 27042

rs.initiate({
  _id: "rsLyon",
  members: [ { _id: 0, host: "localhost:27042" } ]
})

➤ 3. Démarrer le ROUTEUR mongos
mongos --configdb configReplSet/localhost:27040,localhost:27041,localhost:27042 --port 27017

5️⃣ Ajouter les shards
mongosh --port 27017

sh.addShard("rsParis/localhost:27041")
sh.addShard("rsLyon/localhost:27042")

6️⃣ Activer le sharding sur la base
sh.enableSharding("noscites")

7️⃣ Sharder la collection
sh.shardCollection("noscites.listings_nested", { city: 1 })

8️⃣ Vérification
sh.status()

Tu dois voir :
2 shards (rsParis / rsLyon)
collection sharded
clé { city: 1 }

Ingestion des données vers le cluster shardé
Adapter Docker-compose :

MONGO_URI: "mongodb://host.docker.internal:27017/noscites"

Puis : 

docker compose run --rm ingest_nested
docker compose run --rm -e CSV_PATH=/data/listings_lyon.csv ingest_nested