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

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, roc_auc_score
import joblib


CODE_SMELL_PREFIX = "code_smell_"
TEST_SMELL_PREFIX = "test_smell_"


# --------------------------------------------------------------------------- #
# Chargement et préparation
# --------------------------------------------------------------------------- #

def load_dataset(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        sys.exit(f"[Erreur] Fichier introuvable : {path}")
    df = pd.read_csv(path)
    print(f"[Info] Dataset chargé : {df.shape[0]} lignes, {df.shape[1]} colonnes.")
    return df


def get_feature_columns(df: pd.DataFrame, prefix: str, exclude_total: bool = True):
    """Récupère les colonnes code_smell_* / test_smell_* (hors colonne *_total)."""
    cols = [c for c in df.columns if c.startswith(prefix)]
    if exclude_total:
        cols = [c for c in cols if not c.endswith("_total")]
    return cols


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
    plt.figure(figsize=(max(8, len(test_cols) * 0.6), max(6, len(code_cols) * 0.4)))
    sns.heatmap(pearson_matrix.astype(float), annot=False, cmap="coolwarm", center=0)
    plt.title("Corrélation de Pearson : code smells (lignes) vs test smells (colonnes)")
    plt.xlabel("Test smells")
    plt.ylabel("Code smells")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "heatmap_pearson.png"), dpi=150)
    plt.close()

    print(f"[Info] Matrices de corrélation et heatmap sauvegardées dans {output_dir}")
    return pearson_matrix, spearman_matrix, global_corr


# --------------------------------------------------------------------------- #
# Etape 2 : modèles directionnels (code -> test, test -> code)
# --------------------------------------------------------------------------- #

def train_direction_model(df, feature_cols, target_col, model_name, output_dir):
    """Entraîne un classifieur binaire pour prédire target_col à partir de feature_cols."""
    if target_col not in df.columns or not feature_cols:
        print(f"[Attention] Impossible d'entraîner {model_name} : colonnes manquantes.")
        return None

    X = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    y = pd.to_numeric(df[target_col], errors="coerce").fillna(0).astype(int)

    if y.nunique() < 2:
        print(f"[Attention] Cible {target_col} constante, modèle {model_name} ignoré.")
        return None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

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

    importances = pd.Series(
        clf.feature_importances_, index=feature_cols
    ).sort_values(ascending=False)
    importances.to_csv(os.path.join(output_dir, f"feature_importance_{model_name}.csv"))

    with open(os.path.join(output_dir, f"report_{model_name}.json"), "w") as f:
        json.dump({"classification_report": report, "roc_auc": auc}, f, indent=2)

    joblib.dump(
        {"model": clf, "scaler": scaler, "features": feature_cols},
        os.path.join(output_dir, f"model_{model_name}.joblib"),
    )

    print(f"\n[Modèle: {model_name}]")
    print(f"  Cible          : {target_col}")
    print(f"  Nb features    : {len(feature_cols)}")
    print(f"  Accuracy       : {report['accuracy']:.3f}")
    print(f"  ROC AUC        : {auc if auc is None else round(auc, 3)}")
    print(f"  Top 5 features : {list(importances.head(5).index)}")

    return clf, report, auc


# --------------------------------------------------------------------------- #
# Etape 3 : modèle multi-sortie (prédire les deux smells en même temps)
# --------------------------------------------------------------------------- #

def train_multioutput_model(df, feature_cols, target_cols, output_dir):
    """Modèle multi-sortie prédisant simultanément has_code_smell et has_test_smell."""
    if not all(c in df.columns for c in target_cols):
        print("[Attention] Colonnes cibles manquantes pour le modèle multi-sortie.")
        return None

    X = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)
    Y = df[target_cols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

    X_train, X_test, Y_train, Y_test = train_test_split(
        X, Y, test_size=0.25, random_state=42
    )

    base_clf = RandomForestClassifier(
        n_estimators=300, random_state=42, class_weight="balanced"
    )
    model = MultiOutputClassifier(base_clf)
    model.fit(X_train, Y_train)
    Y_pred = model.predict(X_test)

    reports = {}
    for i, col in enumerate(target_cols):
        reports[col] = classification_report(
            Y_test[col], Y_pred[:, i], output_dict=True, zero_division=0
        )
        print(f"\n[Multi-sortie -> {col}]")
        print(f"  Accuracy : {reports[col]['accuracy']:.3f}")

    with open(os.path.join(output_dir, "report_multioutput.json"), "w") as f:
        json.dump(reports, f, indent=2)

    joblib.dump(
        {"model": model, "features": feature_cols, "targets": target_cols},
        os.path.join(output_dir, "model_multioutput.joblib"),
    )

    return model, reports


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(
        description="Analyse de corrélation et prédiction ML entre code smells et test smells."
    )
    parser.add_argument(
        "--input",
        default="../dataset/final/all_projects.csv",
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

    # 1. Corrélations entre les métriques de code smell et de test smell
    compute_correlations(df, code_cols, test_cols, args.output_dir)

    # 2. Modèle : prédire has_test_smell à partir des métriques de code smell
    train_direction_model(
        df, code_cols, "has_test_smell", "code_to_test", args.output_dir
    )

    # 3. Modèle : prédire has_code_smell à partir des métriques de test smell
    train_direction_model(
        df, test_cols, "has_code_smell", "test_to_code", args.output_dir
    )

    # 4. Modèle multi-sortie : prédire les deux simultanément
    all_feature_cols = code_cols + test_cols
    train_multioutput_model(
        df, all_feature_cols, ["has_code_smell", "has_test_smell"], args.output_dir
    )

    print(f"\n[Terminé] Tous les résultats sont sauvegardés dans : {args.output_dir}")


if __name__ == "__main__":
    main()