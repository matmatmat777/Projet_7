import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import math
import ast

# =============================
# CONFIG
# =============================
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "noscites")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "listings_nested")
CSV_PATH = os.getenv("CSV_PATH", "/data/listings_paris.csv")


# =============================
# HELPERS
# =============================

#problèmes de décodages de caractères Unicode avec MongoDB, on sanitize avant d'envoyer
def clean_for_mongo(obj):
    """
    Nettoie récursivement un objet pour enlever les caractères Unicode invalides
    qui font planter l'encodage UTF-8 côté MongoDB.
    """
    import collections.abc

    # Chaînes de caractères : on supprime les surrogates / caractères invalides
    if isinstance(obj, str):
        # encode/decode en ignorant les caractères non-encodables
        return obj.encode("utf-8", "ignore").decode("utf-8", "ignore")

    # Dictionnaire : on nettoie les clés et les valeurs
    if isinstance(obj, dict):
        return {clean_for_mongo(k): clean_for_mongo(v) for k, v in obj.items()}

    # Listes / tuples / autres itérables
    if isinstance(obj, collections.abc.Sequence) and not isinstance(obj, (bytes, bytearray)):
        return [clean_for_mongo(x) for x in obj]

    # Autres types : on laisse tel quel (int, float, bool, None, etc.)
    return obj

def is_nan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def clean_str(v):
    if is_nan(v):
        return None
    v = str(v).strip()
    return v.encode("utf-8", "ignore").decode("utf-8", "ignore")


def to_bool(v):
    if is_nan(v):
        return None
    if isinstance(v, bool):
        return v
    v = str(v).strip().lower()
    if v in ("true", "t", "1", "yes", "y"):
        return True
    if v in ("false", "f", "0", "no", "n"):
        return False
    return None


def to_int(v):
    if is_nan(v):
        return None
    try:
        return int(float(v))
    except:
        return None


def to_float(v):
    if is_nan(v):
        return None
    try:
        return float(v)
    except:
        return None


def to_date(v):
    if is_nan(v):
        return None
    v = str(v).strip()
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(v, fmt)
        except:
            pass
    return None


def parse_list(v):
    if is_nan(v):
        return []
    v = str(v).strip()
    if v.startswith("[") and v.endswith("]"):
        try:
            return ast.literal_eval(v)
        except:
            return [clean_str(v)]
    return [clean_str(v)]


def detect_city(path):
    name = os.path.basename(path).lower()
    if "paris" in name:
        return "Paris"
    if "lyon" in name:
        return "Lyon"
    return "Unknown"


# =============================
# BUILD NESTED DOC
# =============================
def build_nested(row, city):
    def get(col):
        return row[col] if col in row and not is_nan(row[col]) else None

    doc = {
        "city": city,
        "id": to_int(get("id")),
        "listing_url": clean_str(get("listing_url")),
    }

    # Bloc scrape
    scrape = {
        "scrape_id": to_int(get("scrape_id")),
        "last_scraped": to_date(get("last_scraped")),
        "source": clean_str(get("source")),
    }
    scrape = {k: v for k, v in scrape.items() if v is not None}
    if scrape:
        doc["scrape"] = scrape

    # Bloc basic_info
    basic_info = {
        "name": clean_str(get("name")),
        "description": clean_str(get("description")),
        "neighborhood_overview": clean_str(get("neighborhood_overview")),
        "picture_url": clean_str(get("picture_url")),
        "property_type": clean_str(get("property_type")),
        "room_type": clean_str(get("room_type")),
        "accommodates": to_int(get("accommodates")),
        "bathrooms": to_float(get("bathrooms")),
        "bathrooms_text": clean_str(get("bathrooms_text")),
        "bedrooms": to_int(get("bedrooms")),
        "beds": to_int(get("beds")),
        "amenities": parse_list(get("amenities")),
        "price": to_float(get("price")),
        "license": clean_str(get("license")),
        "instant_bookable": to_bool(get("instant_bookable")),
    }
    basic_info = {k: v for k, v in basic_info.items() if v not in (None, [])}
    if basic_info:
        doc["basic_info"] = basic_info

    # Bloc host
    host = {
        "host_id": to_int(get("host_id")),
        "host_url": clean_str(get("host_url")),
        "host_name": clean_str(get("host_name")),
        "host_since": to_date(get("host_since")),
        "host_location": clean_str(get("host_location")),
        "host_about": clean_str(get("host_about")),
        "host_response_time": clean_str(get("host_response_time")),
        "host_response_rate": clean_str(get("host_response_rate")),
        "host_acceptance_rate": clean_str(get("host_acceptance_rate")),
        "host_is_superhost": to_bool(get("host_is_superhost")),
        "host_thumbnail_url": clean_str(get("host_thumbnail_url")),
        "host_picture_url": clean_str(get("host_picture_url")),
        "host_neighbourhood": clean_str(get("host_neighbourhood")),
        "host_verifications": parse_list(get("host_verifications")),
        "host_has_profile_pic": to_bool(get("host_has_profile_pic")),
        "host_identity_verified": to_bool(get("host_identity_verified")),
    }
    host = {k: v for k, v in host.items() if v not in (None, [])}
    if host:
        doc["host"] = host

    # Bloc location
    location = {
        "neighbourhood": clean_str(get("neighbourhood")),
        "neighbourhood_cleansed": clean_str(get("neighbourhood_cleansed")),
        "neighbourhood_group_cleansed": clean_str(get("neighbourhood_group_cleansed")),
        "latitude": to_float(get("latitude")),
        "longitude": to_float(get("longitude")),
    }
    location = {k: v for k, v in location.items() if v is not None}
    if location:
        doc["location"] = location

    # Bloc reviews (simple)
    reviews = {
        "number_of_reviews": to_int(get("number_of_reviews")),
        "number_of_reviews_ltm": to_int(get("number_of_reviews_ltm")),
        "number_of_reviews_l30d": to_int(get("number_of_reviews_l30d")),
        "first_review": to_date(get("first_review")),
        "last_review": to_date(get("last_review")),
        "reviews_per_month": to_float(get("reviews_per_month")),
    }
    reviews = {k: v for k, v in reviews.items() if v is not None}
    if reviews:
        doc["reviews"] = reviews

    return doc


# =============================
# MAIN
# =============================
def main():
    print("DEBUG MONGO_URI =", MONGO_URI)

    print(f"[NESTED] Lecture CSV : {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    city = detect_city(CSV_PATH)
    print(f"[NESTED] Ville détectée : {city}")

    client = MongoClient(MONGO_URI)
    coll = client[DB_NAME][COLLECTION_NAME]

    docs = []
    for _, row in df.iterrows():
        raw_doc = build_nested(row, city)       # document brut
        clean_doc = clean_for_mongo(raw_doc)    # 🔥 nettoyage UTF-8 ici
        docs.append(clean_doc)

    print(f"[NESTED] Insertion de {len(docs)} documents dans {DB_NAME}.{COLLECTION_NAME}")
    #coll.delete_many({})
    coll.insert_many(docs)
    print("[NESTED] ✔ Terminé.")


if __name__ == "__main__":
    main()
