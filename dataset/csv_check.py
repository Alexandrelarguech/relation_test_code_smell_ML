import pandas as pd
import os
import re

def extract_relative_key(path):
    """Extrait la partie du chemin à partir de src/main ou src/test."""
    if pd.isna(path):
        return ""
    p = str(path).replace("\\", "/").lower()
    match = re.search(r"src/(main|test)/java/(.+)", p)
    if match:
        return match.group(2).replace(".java", "")  # ex: org/apache/commons/lang3/annotationutils
    return p

ck = pd.read_csv("metrics/commons-lang/class.csv")
ts = pd.read_csv("test_smells/commons-lang.csv")
cs = pd.read_csv("code_smells/commons-lang.csv", on_bad_lines="skip")

print("=== CK (5 clés main) ===")
ck_main = ck[ck["file"].str.contains("/main/|\\\\main\\\\", case=False, na=False)]
for f in ck_main["file"].head(5):
    print(" ", extract_relative_key(f))

print("\n=== TEST SMELLS (5 clés) ===")
for f in ts["TestFilePath"].head(5):
    print(" ", extract_relative_key(f))

print("\n=== CODE SMELLS (5 clés) ===")
for f in cs["File"].head(5):
    print(" ", extract_relative_key(f))