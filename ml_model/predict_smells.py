"""
Analyse de corrélation et modèle ML entre code smells et test smells.

Entrée attendue : dataset/final/all_projects.csv (généré par
dataset_transformer/build_paired_dataset.py, cf. étape 9 du README).

Colonnes utilisées dans le dataset final :
    - project, class_key, class_name, class_file, test_file
    - has_code_smell, code_smell_total, code_smell_<Rule>...
    - has_test_smell, test_smell_total, test_smell_<Colonne>...

Ce script réalise :
    1. Le chargement du dataset final.
    2. Le calcul des corrélations (Pearson + Spearman) entre chaque code
       smell et chaque test smell, ainsi qu'une corrélation globale entre
       has_code_smell et has_test_smell. Calculé uniquement sur les paires
       classe/test réellement appariées (class_file et test_file tous deux
       renseignés) : le dataset final contient aussi des lignes à un seul
       côté (classe sans test associé retrouvé, ou test sans classe associée
       retrouvée), qui n'apportent pas d'information sur une co-occurrence
       réelle et diluent fortement le signal si on les inclut.
    3. Un modèle de classification prédisant la présence de test smell
       à partir des code smells (direction code -> test).
    4. Un modèle de classification prédisant la présence de code smell
       à partir des test smells (direction test -> code).
    5. La sauvegarde des résultats (CSV, PNG, rapports JSON, modèles
       .joblib) dans un dossier de sortie.

Note : les modèles ML (points 3 et 4) restent entraînés sur le dataset complet,
car has_code_smell et has_test_smell valent tous les deux 1 pour 100% des
paires réellement appariées (une classe n'apparaît dans le dataset de code
smells que si elle a au moins un smell) : restreindre les modèles aux paires
appariées supprimerait toute variance de la cible et rendrait l'entraînement
impossible.

Dépendances :
    pip install pandas numpy scipy scikit-learn matplotlib seaborn joblib

Usage :
    python predict_smells.py \
        --input dataset/final/all_projects.csv \
        --output-dir dataset/ml_results
"""

import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, GroupShuffleSplit
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import joblib


CODE_SMELL_PREFIX = "code_smell_"
TEST_SMELL_PREFIX = "test_smell_"

# Colonnes de métadonnées connues qui héritent parfois du préfixe test_smell_ /
# code_smell_ lors de la fusion (chemins de fichiers, identifiants de projet...)
# mais qui ne sont PAS des indicateurs de smell et doivent être exclues des features.
KNOWN_METADATA_COLUMNS = {
    "test_smell_App",
    "test_smell_Version",
    "test_smell_TestFilePath",
    "test_smell_RelativeTestFilePath",
    "test_smell_RelativeProductionFilePath",
    "test_smell_TestFileName",
    "test_smell_ProductionFileName",
    "test_smell_NumberOfMethods",
}


# --------------------------------------------------------------------------- #
# Chargement et préparation
# --------------------------------------------------------------------------- #

def load_dataset(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        sys.exit(f"[Erreur] Fichier introuvable : {path}")
    df = pd.read_csv(path)
    print(f"[Info] Dataset chargé : {df.shape[0]} lignes, {df.shape[1]} colonnes.")
    return df



def get_feature_columns(df: pd.DataFrame, prefix: str, exclude_total: bool = True,
                        min_numeric_ratio: float = 0.5):
    """Récupère les colonnes code_smell_* / test_smell_* utilisables comme features.

    Exclut :
      - la colonne *_total (agrégat, pas une feature individuelle)
      - les colonnes de métadonnées connues (App, Version, chemins de fichiers...)
      - toute colonne dont moins de `min_numeric_ratio` des valeurs sont
        convertibles en nombre (signe qu'il s'agit de texte/chemin, pas d'un
        compteur de smell), pour éviter les corrélations artefacts.
    """
    cols = [c for c in df.columns if c.startswith(prefix)]
    if exclude_total:
        cols = [c for c in cols if not c.endswith("_total")]

    kept, dropped = [], []
    for c in cols:
        if c in KNOWN_METADATA_COLUMNS:
            dropped.append((c, "colonne de métadonnées connue (app/version/chemin de fichier)"))
            continue
        numeric = pd.to_numeric(df[c], errors="coerce")
        numeric_ratio = numeric.notna().mean()
        if numeric_ratio < min_numeric_ratio:
            dropped.append((c, f"valeurs majoritairement non numériques ({numeric_ratio:.0%} convertibles)"))
            continue
        kept.append(c)

    if dropped:
        print(f"[Info] {len(dropped)} colonnes exclues du préfixe '{prefix}' "
              f"(métadonnées ou non numériques) :")
        for c, reason in dropped:
            print(f"    - {c} : {reason}")

    return kept


# --------------------------------------------------------------------------- #
# Etape 1 : corrélations
# --------------------------------------------------------------------------- #

def compute_correlations(df, code_cols, test_cols, output_dir):
    """Corrélation Pearson et Spearman entre chaque paire (code smell, test smell)."""
    pearson_matrix = pd.DataFrame(index=code_cols, columns=test_cols, dtype=float)
    spearman_matrix = pd.DataFrame(index=code_cols, columns=test_cols, dtype=float)

    for c_col in code_cols:
        x = pd.to_numeric(df[c_col], errors="coerce").fillna(0)
        for t_col in test_cols:
            y = pd.to_numeric(df[t_col], errors="coerce").fillna(0)
            if x.std() == 0 or y.std() == 0:
                pearson_matrix.loc[c_col, t_col] = np.nan
                spearman_matrix.loc[c_col, t_col] = np.nan
                continue
            r_p, _ = pearsonr(x, y)
            r_s, _ = spearmanr(x, y)
            pearson_matrix.loc[c_col, t_col] = r_p
            spearman_matrix.loc[c_col, t_col] = r_s

    pearson_matrix.to_csv(os.path.join(output_dir, "correlation_pearson.csv"))
    spearman_matrix.to_csv(os.path.join(output_dir, "correlation_spearman.csv"))

    # Corrélation globale has_code_smell / has_test_smell (indicateurs binaires)
    global_corr = None
    if "has_code_smell" in df.columns and "has_test_smell" in df.columns:
        a = df["has_code_smell"].fillna(0)
        b = df["has_test_smell"].fillna(0)
        if a.std() > 0 and b.std() > 0:
            r_p, p_p = pearsonr(a, b)
            r_s, p_s = spearmanr(a, b)
            global_corr = {
                "pearson_r": r_p, "pearson_pvalue": p_p,
                "spearman_r": r_s, "spearman_pvalue": p_s,
            }
            with open(os.path.join(output_dir, "global_correlation.json"), "w") as f:
                json.dump(global_corr, f, indent=2)
            print(
                f"[Info] Corrélation globale has_code_smell / has_test_smell : "
                f"Pearson r={r_p:.3f} (p={p_p:.4f}), Spearman r={r_s:.3f} (p={p_s:.4f})"
            )
        else:
            print("[Attention] has_code_smell ou has_test_smell est constant, "
                  "corrélation globale non calculée.")

    # Heatmap Pearson (code smells en lignes, test smells en colonnes)
    # vmin/vmax fixés à -1/1 pour que Pearson et Spearman soient comparables visuellement
    plt.figure(figsize=(max(8, len(test_cols) * 0.6), max(6, len(code_cols) * 0.4)))
    sns.heatmap(
        pearson_matrix.astype(float), annot=False, cmap="coolwarm",
        center=0, vmin=-1, vmax=1,
    )
    plt.title("Pearson correlation : code smells (rows) vs test smells (columns)")
    plt.xlabel("Test smells")
    plt.ylabel("Code smells")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "heatmap_pearson.png"), dpi=150)
    plt.close()

    # Heatmap Spearman (même échelle de couleur que Pearson pour comparaison directe)
    plt.figure(figsize=(max(8, len(test_cols) * 0.6), max(6, len(code_cols) * 0.4)))
    sns.heatmap(
        spearman_matrix.astype(float), annot=False, cmap="coolwarm",
        center=0, vmin=-1, vmax=1,
    )
    plt.title("Corrélation de Spearman : code smells (lignes) vs test smells (colonnes)")
    plt.xlabel("Test smells")
    plt.ylabel("Code smells")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "heatmap_spearman.png"), dpi=150)
    plt.close()

    print(f"[Info] Matrices de corrélation et heatmaps (Pearson + Spearman) sauvegardées dans {output_dir}")
    return pearson_matrix, spearman_matrix, global_corr


# --------------------------------------------------------------------------- #
# Etape 2 : modèles directionnels (code -> test, test -> code)
# --------------------------------------------------------------------------- #

def train_direction_model(df, feature_cols, target_col, model_name, output_dir,
                          group_col=None):
    """Entraîne un classifieur binaire pour prédire target_col à partir de feature_cols.

    Diagnostics inclus :
      1. Baseline "classe majoritaire" (DummyClassifier).
      2. Split groupé par projet (si group_col fourni) pour éviter la fuite
         inter-projet.
    """
    if target_col not in df.columns or not feature_cols:
        print(f"[Attention] Impossible d'entraîner {model_name} : colonnes manquantes.")
        return None

    X = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    y = pd.to_numeric(df[target_col], errors="coerce").fillna(0).astype(int)

    if y.nunique() < 2:
        print(f"[Attention] Cible {target_col} constante, modèle {model_name} ignoré.")
        return None

    use_groups = group_col is not None and group_col in df.columns
    if use_groups:
        splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
        train_idx, test_idx = next(splitter.split(X, y, groups=df[group_col]))
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        split_desc = f"groupé par '{group_col}' (pas de fuite inter-projet)"
    else:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.25, random_state=42, stratify=y
        )
        split_desc = "aléatoire simple (stratifié sur la cible)"

    scaler = StandardScaler()
    scaler.fit(X_train)  # conservé pour un usage ultérieur éventuel (ex: modèles linéaires)

    clf = RandomForestClassifier(
        n_estimators=300, max_depth=None, random_state=42, class_weight="balanced"
    )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)[:, 1]

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    try:
        auc = roc_auc_score(y_test, y_proba)
    except ValueError:
        auc = None

    # Baseline : toujours prédire la classe majoritaire du train set
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    baseline_accuracy = dummy.score(X_test, y_test)
    lift = report["accuracy"] - baseline_accuracy

    importances = pd.Series(
        clf.feature_importances_, index=feature_cols
    ).sort_values(ascending=False)
    importances.to_csv(os.path.join(output_dir, f"feature_importance_{model_name}.csv"))

    report_payload = {
        "classification_report": report,
        "roc_auc": auc,
        "baseline_accuracy": baseline_accuracy,
        "accuracy_lift_over_baseline": lift,
        "split": split_desc,
        "class_balance_target": y.value_counts(normalize=True).to_dict(),
    }

    with open(os.path.join(output_dir, f"report_{model_name}.json"), "w") as f:
        json.dump(report_payload, f, indent=2)

    joblib.dump(
        {"model": clf, "scaler": scaler, "features": feature_cols},
        os.path.join(output_dir, f"model_{model_name}.joblib"),
    )

    print(f"\n[Modèle: {model_name}]")
    print(f"  Accuracy              : {report['accuracy']:.3f}")
    print(f"  Baseline : {baseline_accuracy:.3f}")
    print(f"  Gain vs baseline      : {lift:+.3f}"
          + ("  <-- attention, gain faible ou négatif : signal peu fiable" if lift < 0.05 else ""))
    print(f"  Top 5 features        : {list(importances.head(5).index)}")

    return clf, report, auc


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Analyse de corrélation et prédiction ML entre code smells et test smells."
    )
    parser.add_argument(
        "--input",
        default="dataset/final/all_projects.csv",
        help="Chemin vers le dataset final (défaut: dataset/final/all_projects.csv)",
    )
    parser.add_argument(
        "--output-dir",
        default="dataset/ml_results",
        help="Dossier de sortie pour les résultats (défaut: dataset/ml_results)",
    )

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    df = load_dataset(args.input)

    code_cols = get_feature_columns(df, CODE_SMELL_PREFIX)
    test_cols = get_feature_columns(df, TEST_SMELL_PREFIX)

    print(f"[Info] {len(code_cols)} colonnes de code smells détectées.")
    print(f"[Info] {len(test_cols)} colonnes de test smells détectées.")

    if not code_cols or not test_cols:
        sys.exit(
            "[Erreur] Impossible de trouver les colonnes code_smell_* ou "
            "test_smell_*. Vérifie le fichier d'entrée."
        )

    # 1. Corrélation de Pearson (+ Spearman) entre chaque code smell et chaque test smell.
    # Restreinte aux paires réellement appariées (class_file ET test_file renseignés) :
    # la majorité des lignes du dataset final ne représentent qu'un seul côté (classe
    # trouvée uniquement dans les code smells, ou test trouvé uniquement dans les test
    # smells), avec des zéros de remplissage de l'autre côté. Inclure ces lignes noierait
    # le signal réel sous un artefact de construction du dataset.
    matched_df = df[df["class_file"].notna() & df["test_file"].notna()]
    print(f"[Info] {len(matched_df)}/{len(df)} lignes correspondent à une paire "
          f"classe/test réellement appariée (utilisées pour la corrélation).")
    compute_correlations(matched_df, code_cols, test_cols, args.output_dir)

    # 2. Modèle : prédire has_test_smell à partir des code smells (code -> test)
    train_direction_model(
        df, code_cols, "has_test_smell", "code_to_test", args.output_dir,
        group_col="project",
    )

    # 3. Modèle : prédire has_code_smell à partir des test smells (test -> code)
    train_direction_model(
        df, test_cols, "has_code_smell", "test_to_code", args.output_dir,
        group_col="project",
    )

    print(f"\n[Terminé] Tous les résultats sont sauvegardés dans : {args.output_dir}")


if __name__ == "__main__":
    main()