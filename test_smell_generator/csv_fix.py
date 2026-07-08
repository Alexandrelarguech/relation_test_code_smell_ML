import os
import csv

INPUT_DIR = "dataset/tsdetect_input"
FIXED_DIR = "dataset/tsdetect_fixed"
os.makedirs(FIXED_DIR, exist_ok=True)

projects = [
    "spring-boot",
    "quarkus",
    "commons-lang",
    "resilience4j",
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
    input_csv = os.path.join(INPUT_DIR, f"{name}.csv")
    fixed_csv = os.path.join(FIXED_DIR, f"{name}.csv")

    if not os.path.exists(input_csv):
        print(f"[MANQUANT] {name}")
        continue

    rows = []
    seen_files = set()

    with open(input_csv, encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        for row in reader:
            test_path = row.get("FilePath", "").strip()
            if not test_path or test_path in seen_files:
                continue
            if not os.path.exists(test_path):
                continue
            seen_files.add(test_path)
            rows.append([name, test_path, ""])

    with open(fixed_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

    print(f"[OK] {name} — {len(rows)} fichiers de test")