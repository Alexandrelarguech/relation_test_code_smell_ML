import subprocess, os, shutil, glob

PROJECTS_DIR = "../dataset/projects"
INPUT_DIR    = "../dataset/tsdetect_input"
os.makedirs(INPUT_DIR, exist_ok=True)

projects = ["spring-boot", "quarkus", "commons-lang", "resilience4j", "hibernate-orm"]

for name in projects:
    output_csv = f"{INPUT_DIR}/{name}.csv"
    if os.path.exists(output_csv):
        print(f"[SKIP] {name}")
        continue

    print(f"[FileDetector] {name}...")
    result = subprocess.run(
        ["java", "-jar", "tools/TestFileDetector.jar", f"{PROJECTS_DIR}/{name}"],
        capture_output=True, text=True, timeout=120
    )

    # Chercher le CSV généré dans le répertoire courant
    generated = glob.glob("*.csv")
    if generated:
        # Prendre le plus récent
        latest = max(generated, key=os.path.getmtime)
        shutil.move(latest, output_csv)
        with open(output_csv, encoding="utf-8", errors="ignore") as f:
            count = sum(1 for _ in f)
        print(f"[OK] {name} — {count} fichiers de test détectés")
    else:
        print(f"[ERREUR] {name} : {result.stderr[:200]}")