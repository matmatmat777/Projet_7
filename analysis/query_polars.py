import polars as pl

def main():
    print("Chargement du CSV avec Polars...")
    df = pl.read_csv("/data/listings_paris.csv")

    print("Exécution de la requête analytique Polars...")

    # Nombre de lignes
    print(f"Nombre de lignes dans le fichier : {df.height}")

    # Calcul du taux d'occupation mensuel
    df = df.with_columns([
        (1 - (pl.col("availability_30") / 30)).alias("taux_reservation_mensuel")
    ])

    print("\nCalcul du taux de réservation mensuel par type de logement...")

    # Moyenne par type de logement
    result = (
        df.group_by("room_type")
          .agg([
              pl.len().alias("nombre_de_logements"),
              pl.mean("taux_reservation_mensuel").alias("taux_res_moyen")
          ])
          .sort("taux_res_moyen", descending=True)
    )

    print("\n📊 Résultat : taux de réservation mensuel moyen par type de logement")
    print(result)

    # médiane des nombre d’avis pour tous les logements
    median_reviews = df.select(pl.median("number_of_reviews").alias("median_number_of_reviews"))
    print("\nMédiane du nombre d'avis pour tous les logements :")
    print(median_reviews)

    print("\nAnalyse terminée avec succès !")

    # Moyenne par type d'hote'
    result = (
    df.group_by("host_is_superhost")
      .agg(
          pl.median("number_of_reviews").alias("median_reviews")
      )
      .sort("host_is_superhost", descending=True)
)

    print("\nMédiane du nombre d'avis par catégorie d'hôte :")
    print(result)


#    print("\nDEBUG : colonnes du fichier →")
#    print(df.columns)


if __name__ == "__main__":
    main()
