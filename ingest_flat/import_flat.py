import os
import glob
import math
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# =============================
# CONFIG
# =============================
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "noscites")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "listings_flat")
DATA_FOLDER = "/data"


# =============================
# HELPERS
# =============================
def clean_unicode(s):
    if isinstance(s, str):
        return s.encode("utf-8", "ignore").decode("utf-8", "ignore")
    return s


def safe_date(value):
    """Convertit une date en string ISO (Atlas friendly) ou None."""
    if value is None or pd.isna(value):
        return None

    if isinstance(value, str):
        value = value.strip()
        for fmt in [
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%Y-%m-%dT%H:%M:%S",
            "%d/%m/%Y",
        ]:
            try:
                dt = datetime.strptime(value, fmt)
                return dt.date().isoformat()  # <-- STRING ISO (Atlas OK)
            except:
                pass
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    return None


def clean_for_mongo(obj):
    """
    Nettoie récursivement pour Atlas :
    - remove NaT / NaN
    - convertit datetime -> string ISO
    - convertit numpy -> Python natif
    - nettoie les unicode
    """
    import numpy as np
    import collections.abc

    if obj is None:
        return None

    # Pandas NaT / NaN
    if isinstance(obj, float) and math.isnan(obj):
        return None

    if isinstance(obj, pd.Timestamp):
        if obj is pd.NaT:
            return None
        return obj.to_pydatetime().date().isoformat()

    # datetime → string ISO (Atlas-friendly)
    if isinstance(obj, datetime):
        return obj.date().isoformat()

    # numpy → Python natif
    if isinstance(obj, (np.integer, np.int64, np.int32)):
        return int(obj)

    if isinstance(obj, (np.floating, np.float64, np.float32)):
        return float(obj)

    # strings
    if isinstance(obj, str):
        return clean_unicode(obj)

    # dict → clean récursif
    if isinstance(obj, dict):
        return {clean_for_mongo(k): clean_for_mongo(v) for k, v in obj.items()}

    # list → clean récursif
    if isinstance(obj, list):
        return [clean_for_mongo(v) for v in obj]

    return obj


def is_nan(v):
    return v is None or (isinstance(v, float) and math.isnan(v))


def to_int(v):
    try:
        if is_nan(v): return None
        return int(float(v))
    except:
        return None


def to_float(v):
    try:
        if is_nan(v): return None
        return float(v)
    except:
        return None


def to_str(v):
    if is_nan(v):
        return None
    v = str(v).strip()
    return clean_unicode(v)


def to_bool(v):
    if is_nan(v): return None
    if isinstance(v, bool): return v
    v = str(v).lower()
    return v in ("1", "true", "t", "yes", "y")


def detect_city(filename):
    f = filename.lower()
    if "paris" in f: return "Paris"
    if "lyon" in f: return "Lyon"
    return "Unknown"


# =============================
# MAIN IMPORT
# =============================
def main():
    print("[FLAT] Recherche des CSV dans /data …")

    csv_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))

    if not csv_files:
        print("[ERR] Aucun CSV trouvé")
        return

    print(f"[FLAT] {len(csv_files)} CSV détectés :")
    for f in csv_files:
        print(" -", os.path.basename(f))

    all_rows_df = []

    for csv_path in csv_files:
        city = detect_city(csv_path)
        print(f"\n[FLAT] Lecture : {csv_path}  → Ville = {city}")

        df = pd.read_csv(csv_path)
        df["city"] = city

        # STR
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].apply(to_str)

        # FLOAT
        for col in df.select_dtypes(include=["float"]).columns:
            df[col] = df[col].apply(to_float)

        # INT
        for col in df.select_dtypes(include=["int"]).columns:
            df[col] = df[col].apply(to_int)

        # DATES → STRING ISO (CRUCIAL)
        date_fields = [
            "last_scraped", "host_since", "first_review",
            "last_review", "calendar_last_scraped"
        ]
        for c in date_fields:
            if c in df.columns:
                df[c] = df[c].apply(safe_date)

        # BOOL
        bool_fields = [
            "host_is_superhost",
            "host_has_profile_pic",
            "host_identity_verified",
            "instant_bookable",
            "has_availability"
        ]
        for c in bool_fields:
            if c in df.columns:
                df[c] = df[c].apply(to_bool)

        all_rows_df.append(df)

    # Fusion multi-villes
    final_df = pd.concat(all_rows_df, ignore_index=True)

    print(f"\n[FLAT] Total lignes à importer : {len(final_df)}")

    # Convertit dataframe → dict → nettoyage total
    docs = [clean_for_mongo(doc) for doc in final_df.to_dict(orient="records")]

    # Connexion MongoDB Atlas
    client = MongoClient(MONGO_URI)
    coll = client[DB_NAME][COLLECTION_NAME]

    print(f"[FLAT] Reset collection `{COLLECTION_NAME}`…")
    coll.delete_many({})

    print("[FLAT] Insertion batchée dans Atlas…")

    batch_size = 2000
    for i in range(0, len(docs), batch_size):
        chunk = docs[i:i + batch_size]
        coll.insert_many(chunk)
        print(f"  → {i + len(chunk)}/{len(docs)} insérés")

    print("\n[FLAT] ✔ Import FLAT terminé (ZÉRO erreur NaT / datetime / Unicode)!")


if __name__ == "__main__":
    main()
