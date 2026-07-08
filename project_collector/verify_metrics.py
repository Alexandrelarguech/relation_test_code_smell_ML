import os
import pandas as pd

METRICS_DIR = "dataset/metrics"

for project in os.listdir(METRICS_DIR):
    project_path = f"{METRICS_DIR}/{project}"
    class_csv = f"{project_path}/class.csv"

    if os.path.exists(class_csv):
        df = pd.read_csv(class_csv)
        print(f"[{project}]")
        print(f"  Lignes     : {len(df)}")
        print(f"  Colonnes   : {list(df.columns)}")
        print(f"  Aperçu     :")
        print(df[["class", "wmc", "dit", "cbo", "rfc", "lcom", "loc"]].head(3).to_string())
        print()
    else:
        print(f"[{project}] ❌ class.csv manquant")