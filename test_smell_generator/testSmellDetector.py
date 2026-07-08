import glob
import os
import shutil
import subprocess

FIXED_DIR = "dataset/tsdetect_fixed"
OUTPUT_DIR = "dataset/test_smells"
os.makedirs(OUTPUT_DIR, exist_ok=True)

projects = [
    "commons-lang",
    "resilience4j",
    "spring-boot",
    "quarkus",
    "hibernate-orm",
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
    fixed_csv = os.path.join(FIXED_DIR, f"{name}.csv")
    output_csv = os.path.join(OUTPUT_DIR, f"{name}.csv")

    if os.path.exists(output_csv):
        print(f"[SKIP] {name}")
        continue

    if not os.path.exists(fixed_csv):
        print(f"[MANQUANT] {name} : {fixed_csv}")
        continue

    print(f"[TestSmellDetector] {name}...")
    result = subprocess.run(
        ["java", "-jar", "tools/TestSmellDetector.jar", fixed_csv],
        capture_output=True, text=True,
        timeout=1800
    )

    print(f"  stdout : {result.stdout[:150]}")

    generated = sorted(glob.glob("Output_TestSmellDetection_*.csv"), key=os.path.getmtime, reverse=True)
    if generated:
        shutil.move(generated[0], output_csv)
        with open(output_csv, encoding="utf-8", errors="ignore") as f:
            count = sum(1 for _ in f) - 1
        print(f"[OK] {name} — {count} classes analysées")
    else:
        print(f"[ERREUR] {name} — aucun fichier généré")