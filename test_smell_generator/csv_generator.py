import subprocess, os, shutil, glob

PROJECTS_DIR = "dataset/projects"
INPUT_DIR = "dataset/tsdetect_input"
os.makedirs(INPUT_DIR, exist_ok=True)

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
    project_path = os.path.join(PROJECTS_DIR, name)
    output_csv = os.path.join(INPUT_DIR, f"{name}.csv")
    if os.path.exists(output_csv):
        print(f"[SKIP] {name}")
        continue

    if not os.path.exists(project_path):
        print(f"[CHEMIN MANQUANT] {name} : {project_path}")
        continue

    print(f"[FileDetector] {name}...")
    result = subprocess.run(
        ["java", "-jar", "tools/TestFileDetector.jar", project_path],
        capture_output=True, text=True, timeout=300
    )

    generated = glob.glob("*.csv")
    if generated:
        latest = max(generated, key=os.path.getmtime)
        shutil.move(latest, output_csv)
        with open(output_csv, encoding="utf-8", errors="ignore") as f:
            count = sum(1 for _ in f)
        print(f"[OK] {name} — {count} fichiers de test détectés")
    else:
        print(f"[ERREUR] {name} : {result.stderr[:200]}")