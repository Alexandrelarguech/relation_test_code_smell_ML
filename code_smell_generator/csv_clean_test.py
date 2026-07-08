import pandas as pd
import os

OUTPUT_DIR = "dataset/code_smells"
projects = [
    "quarkus",
    "commons-lang",
    "resilience4j",
    "hibernate-orm",
    "spring-boot",
    "elasticsearch",
    "okhttp",
    "dubbo",
    "guava",
    "mockito",
    "junit5",
    "netty",
    "kafka",
    "cassandra",
    "pulsar",
]

for name in projects:
    csv_path = os.path.join(OUTPUT_DIR, f"{name}.csv")
    if not os.path.exists(csv_path):
        print(f"[MANQUANT] {name}")
        continue

    df = pd.read_csv(csv_path, encoding="utf-8", on_bad_lines="skip")
    total_avant = len(df)

    file_col = "File"
    if file_col not in df.columns:
        print(f"[{name}] Colonnes disponibles : {list(df.columns)}")
        continue

    mask_test = df[file_col].str.contains(
        r"[/\\]test[/\\]",
        case=False,
        regex=True,
        na=False
    )
    df_clean = df[~mask_test]

    total_apres = len(df_clean)
    total_supprime = total_avant - total_apres

    df_clean.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"[{name}] {total_avant} → {total_apres} lignes "
          f"({total_supprime} lignes test supprimées)")