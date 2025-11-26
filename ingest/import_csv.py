import os
import pandas as pd
from pymongo import MongoClient
import math

MONGO_URI = os.getenv("MONGO_URI", "mongodb://root:example@mongo:27017/")
DB_NAME = os.getenv("MONGO_DB", "noscites")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "listings_paris")
CSV_PATH = os.getenv("CSV_PATH", "/data/listings_paris.csv")

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

def is_nan(value) -> bool:
    """Retourne True si la valeur est NaN / vide."""
    return value is None or (isinstance(value, float) and math.isnan(value))


def to_bool(value):
    """Convertit t/f, True/False, 1/0 en booléen Python."""
    if is_nan(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    v = str(value).strip().lower()
    if v in ("t", "true", "1", "yes", "y"):
        return True
    if v in ("f", "false", "0", "no", "n"):
        return False
    return None


def parse_amenities(value):
    """
    Les amenities viennent souvent comme une chaîne de type:
    ["Wifi", "Kitchen", "Heating"]
    On essaie de la convertir en liste Python propre.
    """
    if is_nan(value):
        return []
    v = str(value).strip()
    # Cas simple: déjà une liste style JSON
    if v.startswith("[") and v.endswith("]"):
        try:
            import ast
            lst = ast.literal_eval(v)
            if isinstance(lst, list):
                return [str(x) for x in lst]
        except Exception:
            pass
    # Sinon on retourne une liste avec la chaîne brute
    return [v]


def main():
    print(f"Connexion à MongoDB : {MONGO_URI}")
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    print(f"Lecture du fichier CSV : {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    print(f"{len(df)} lignes lues, transformation en JSON imbriqué...")

    docs = []

    for _, row in df.iterrows():
        # Helpers locaux
        def get(col):
            return row[col] if col in df.columns and not is_nan(row[col]) else None

        # Document principal = 1 annonce
        doc = {
            "id": int(get("id")) if get("id") is not None else None,
            "listing_url": get("listing_url"),
        }

        # --- Bloc scrape / métadonnées ---
        scrape = {
            "scrape_id": get("scrape_id"),
            "last_scraped": get("last_scraped"),
            "source": get("source"),
        }
        # On enlève les clés None pour alléger
        scrape = {k: v for k, v in scrape.items() if v is not None}
        if scrape:
            doc["scrape"] = scrape

        # --- Bloc basic_info ---
        basic_info = {
            "name": get("name"),
            "description": get("description"),
            "neighborhood_overview": get("neighborhood_overview"),
            "picture_url": get("picture_url"),
            "property_type": get("property_type"),
            "room_type": get("room_type"),
            "accommodates": get("accommodates"),
            "bathrooms": get("bathrooms"),
            "bathrooms_text": get("bathrooms_text"),
            "bedrooms": get("bedrooms"),
            "beds": get("beds"),
            "amenities": parse_amenities(get("amenities")),
            "price": get("price"),
            "license": get("license"),
            "instant_bookable": to_bool(get("instant_bookable")),
        }
        basic_info = {k: v for k, v in basic_info.items() if v is not None and v != []}
        if basic_info:
            doc["basic_info"] = basic_info

        # --- Bloc host ---
        host = {
            "host_id": get("host_id"),
            "host_url": get("host_url"),
            "host_name": get("host_name"),
            "host_since": get("host_since"),
            "host_location": get("host_location"),
            "host_about": get("host_about"),
            "host_response_time": get("host_response_time"),
            "host_response_rate": get("host_response_rate"),
            "host_acceptance_rate": get("host_acceptance_rate"),
            "host_is_superhost": to_bool(get("host_is_superhost")),
            "host_thumbnail_url": get("host_thumbnail_url"),
            "host_picture_url": get("host_picture_url"),
            "host_neighbourhood": get("host_neighbourhood"),
            "host_listings_count": get("host_listings_count"),
            "host_total_listings_count": get("host_total_listings_count"),
            "host_verifications": parse_amenities(get("host_verifications")),
            "host_has_profile_pic": to_bool(get("host_has_profile_pic")),
            "host_identity_verified": to_bool(get("host_identity_verified")),
        }
        host = {
            k: v
            for k, v in host.items()
            if v is not None and not (isinstance(v, list) and len(v) == 0)
        }
        if host:
            doc["host"] = host

        # --- Bloc location ---
        location = {
            "neighbourhood": get("neighbourhood"),
            "neighbourhood_cleansed": get("neighbourhood_cleansed"),
            "neighbourhood_group_cleansed": get("neighbourhood_group_cleansed"),
            "latitude": get("latitude"),
            "longitude": get("longitude"),
        }
        location = {k: v for k, v in location.items() if v is not None}
        if location:
            doc["location"] = location

        # --- Bloc stay_rules ---
        stay_rules = {
            "minimum_nights": get("minimum_nights"),
            "maximum_nights": get("maximum_nights"),
            "minimum_minimum_nights": get("minimum_minimum_nights"),
            "maximum_minimum_nights": get("maximum_minimum_nights"),
            "minimum_maximum_nights": get("minimum_maximum_nights"),
            "maximum_maximum_nights": get("maximum_maximum_nights"),
            "minimum_nights_avg_ntm": get("minimum_nights_avg_ntm"),
            "maximum_nights_avg_ntm": get("maximum_nights_avg_ntm"),
        }
        stay_rules = {k: v for k, v in stay_rules.items() if v is not None}
        if stay_rules:
            doc["stay_rules"] = stay_rules

        # --- Bloc availability ---
        availability = {
            "calendar_updated": get("calendar_updated"),
            "has_availability": to_bool(get("has_availability")),
            "availability_30": get("availability_30"),
            "availability_60": get("availability_60"),
            "availability_90": get("availability_90"),
            "availability_365": get("availability_365"),
            "calendar_last_scraped": get("calendar_last_scraped"),
        }
        availability = {k: v for k, v in availability.items() if v is not None}
        if availability:
            doc["availability"] = availability

        # --- Bloc reviews ---
        review_scores = {
            "review_scores_rating": get("review_scores_rating"),
            "review_scores_accuracy": get("review_scores_accuracy"),
            "review_scores_cleanliness": get("review_scores_cleanliness"),
            "review_scores_checkin": get("review_scores_checkin"),
            "review_scores_communication": get("review_scores_communication"),
            "review_scores_location": get("review_scores_location"),
            "review_scores_value": get("review_scores_value"),
        }
        review_scores = {k: v for k, v in review_scores.items() if v is not None}

        reviews = {
            "number_of_reviews": get("number_of_reviews"),
            "number_of_reviews_ltm": get("number_of_reviews_ltm"),
            "number_of_reviews_l30d": get("number_of_reviews_l30d"),
            "first_review": get("first_review"),
            "last_review": get("last_review"),
            "reviews_per_month": get("reviews_per_month"),
        }
        if review_scores:
            reviews["review_scores"] = review_scores
        reviews = {k: v for k, v in reviews.items() if v is not None}
        if reviews:
            doc["reviews"] = reviews

        # --- Bloc host_listings_summary ---
        host_listings_summary = {
            "calculated_host_listings_count": get("calculated_host_listings_count"),
            "calculated_host_listings_count_entire_homes": get(
                "calculated_host_listings_count_entire_homes"
            ),
            "calculated_host_listings_count_private_rooms": get(
                "calculated_host_listings_count_private_rooms"
            ),
            "calculated_host_listings_count_shared_rooms": get(
                "calculated_host_listings_count_shared_rooms"
            ),
        }
        host_listings_summary = {
            k: v for k, v in host_listings_summary.items() if v is not None
        }
        if host_listings_summary:
            doc["host_listings_summary"] = host_listings_summary

        # Nettoyage du document pour enlever les caractères Unicode invalides
        safe_doc = clean_for_mongo(doc)
        docs.append(safe_doc)


    print(f"{len(docs)} documents construits, insertion dans MongoDB...")
    if docs:
        collection.delete_many({})  # optionnel : on nettoie avant
        collection.insert_many(docs)
        print(f"{len(docs)} documents imbriqués insérés dans {DB_NAME}.{COLLECTION_NAME}")
    else:
        print("Aucun document à insérer.")


if __name__ == "__main__":
    main()
