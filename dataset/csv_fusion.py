import pandas as pd
import os
import re

PROJECTS      = ["commons-lang", "resilience4j", "quarkus", "hibernate-orm", "spring-boot"]
METRICS_DIR   = "metrics"
TS_DIR        = "test_smells"
CS_DIR        = "code_smells"
OUTPUT_DIR    = "final"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TEST_SMELL_COLS = [
    "Assertion Roulette", "Conditional Test Logic", "Constructor Initialization",
    "Default Test", "EmptyTest", "Exception Catching Throwing", "General Fixture",
    "Mystery Guest", "Print Statement", "Redundant Assertion", "Sensitive Equality",
    "Verbose Test", "Sleepy Test", "Eager Test", "Lazy Test", "Duplicate Assert",
    "Unknown Test", "IgnoredTest", "Resource Optimism", "Magic Number Test", "Dependent Test"
]

CODE_SMELL_RULES = [
    "GodClass", "ExcessiveClassLength", "ExcessiveMethodLength",
    "ExcessiveParameterList", "TooManyFields", "TooManyMethods",
    "CyclomaticComplexity", "CouplingBetweenObjects"
]

def extract_key(path):
    """Extrait org/package/ClassName sans extension depuis un chemin absolu ou relatif."""
    if pd.isna(path):
        return ""
    p = str(path).replace("\\", "/").lower()
    match = re.search(r"src/(main|test)/java/(.+)", p)
    if match:
        return match.group(2).replace(".java", "")
    return ""

all_projects = []

for project in PROJECTS:
    print(f"\n{'='*50}")
    print(f"Assemblage : {project}")

    ck_path = f"{METRICS_DIR}/{project}/class.csv"
    if not os.path.exists(ck_path):
        print(f"  [SKIP] CK manquant")
        continue
    ck = pd.read_csv(ck_path)
    ck = ck[ck["file"].str.contains("/main/|\\\\main\\\\", case=False, na=False)]
    ck["key"] = ck["file"].apply(extract_key)
    ck = ck[ck["key"] != ""]
    print(f"  CK        : {len(ck)} classes de production")

    cs_path = f"{CS_DIR}/{project}.csv"
    if not os.path.exists(cs_path):
        print(f"  [SKIP] Code smells manquant")
        continue
    cs = pd.read_csv(cs_path, on_bad_lines="skip")
    cs["key"] = cs["File"].apply(extract_key)
    cs = cs[cs["key"] != ""]
    cs["value"] = 1
    cs_pivot = cs.pivot_table(
        index="key", columns="Rule", values="value", aggfunc="max"
    ).fillna(0).astype(int).reset_index()
    cs_cols = [c for c in CODE_SMELL_RULES if c in cs_pivot.columns]
    cs_pivot = cs_pivot[["key"] + cs_cols]
    print(f"  CodeSmells: {len(cs_pivot)} classes avec violations")

    ts_path = f"{TS_DIR}/{project}.csv"
    if not os.path.exists(ts_path):
        print(f"  [SKIP] Test smells manquant")
        continue
    ts = pd.read_csv(ts_path)
    ts["key"] = ts["TestFilePath"].apply(extract_key)
    ts = ts[ts["key"] != ""]
    for col in TEST_SMELL_COLS:
        if col in ts.columns:
            ts[col] = ts[col].map({True: 1, False: 0, "True": 1, "False": 0}).fillna(0).astype(int)
    ts_agg = ts.groupby("key")[TEST_SMELL_COLS].max().reset_index()

    ts_agg["prod_key"] = ts_agg["key"].apply(
        lambda k: re.sub(r"tests?$", "", k)
    )
    print(f"  TestSmells: {len(ts_agg)} fichiers de test")

    merged = ck.merge(cs_pivot, on="key", how="left")
    for col in cs_cols:
        merged[col] = merged[col].fillna(0).astype(int)

    merged = merged.merge(ts_agg, left_on="key", right_on="prod_key", how="left", suffixes=("", "_ts"))
    for col in TEST_SMELL_COLS:
        if col in merged.columns:
            merged[col] = merged[col].fillna(0).astype(int)

    merged["project"] = project
    drop_cols = ["key_ts", "prod_key"]
    merged = merged.drop(columns=[c for c in drop_cols if c in merged.columns])

    matched_ts = (merged[TEST_SMELL_COLS].sum(axis=1) > 0).sum()
    matched_cs = (merged[cs_cols].sum(axis=1) > 0).sum()
    print(f"  Classes avec ≥1 code smell  : {matched_cs}")
    print(f"  Classes avec ≥1 test smell  : {matched_ts}")
    print(f"  Dataset : {len(merged)} lignes")

    all_projects.append(merged)

if all_projects:
    final = pd.concat(all_projects, ignore_index=True)
    out_path = f"{OUTPUT_DIR}/dual_smell_dataset.csv"
    final.to_csv(out_path, index=False, encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"Dataset final : {len(final)} classes | {len(final.columns)} colonnes")
    print(f"Sauvegardé    : {out_path}")

    print(f"\nDistribution des smells :")
    for col in cs_cols + TEST_SMELL_COLS:
        if col in final.columns:
            n = int(final[col].sum())
            pct = 100 * n / len(final)
            print(f"  {col:<35} {n:>5} ({pct:.1f}%)")