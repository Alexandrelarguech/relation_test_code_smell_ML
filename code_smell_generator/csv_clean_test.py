import pandas as pd
import os

OUTPUT_DIR = "../dataset/code_smells"
projects   = ["quarkus", "commons-lang", "resilience4j", "hibernate-orm", "spring-boot"]

for name in projects:
    csv_path = f"{OUTPUT_DIR}/{name}.csv"
    if not os.path.exists(csv_path):
        print(f"[MANQUANT] {name}")
        continue

    df = pd.read_csv(csv_path, encoding="utf-8", errors="replace")

    total_avant = len(df)

    # Colonne contenant le chemin du fichier — vérifier le nom exact
    # PMD utilise généralement "File" comme nom de colonne
    file_col = "File"
    if file_col not in df.columns:
        print(f"[{name}] Colonnes disponibles : {list(df.columns)}")
        continue

    # Supprimer toutes les lignes pointant vers src/test/java
    mask_test = df[file_col].str.contains(
        r"[/\\]test[/\\]",
        case=False,
        regex=True,
        na=False
    )
    df_clean = df[~mask_test]

    total_apres  = len(df_clean)
    total_supprime = total_avant - total_apres

    # Sauvegarder
    df_clean.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"[{name}] {total_avant} → {total_apres} lignes "
          f"({total_supprime} lignes test supprimées)")