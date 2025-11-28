import polars as pl

def main():
    print("Chargement du CSV avec Polars...")
    df = pl.read_csv("/data/listings_paris.csv")

    print("Exécution de la requête analytique Polars...")

    # Hauteur du DataFrame
    print(f"Nombre de lignes dans le fichier : {df.height}")

    print("\nAnalyse terminée avec succès !")

if __name__ == "__main__":
    main()
