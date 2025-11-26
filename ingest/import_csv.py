import pandas as pd
from pymongo import MongoClient
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:example@mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "noscites")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "listings_paris")
CSV_PATH = os.getenv("CSV_PATH", "/data/listings_paris.csv")

print(f"Connexion à MongoDB : {MONGO_URI}")
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

print(f"Lecture du fichier CSV : {CSV_PATH}")
df = pd.read_csv(CSV_PATH)

records = df.to_dict(orient="records")
print(f"{len(records)} lignes lues, insertion dans MongoDB...")

if records:
    collection.insert_many(records)
    print(f"{len(records)} documents insérés dans {DB_NAME}.{COLLECTION_NAME}")
else:
    print("Aucun enregistrement trouvé dans le CSV.")
