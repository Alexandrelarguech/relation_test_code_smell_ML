import subprocess
import os

PROJECTS_DIR = "../dataset/projects"
OUTPUT_DIR   = "../dataset/metrics"
CK_JAR       = "tools/ck.jar"

project_paths = {
    "spring-boot":  f"{PROJECTS_DIR}/spring-boot",
    "quarkus":      f"{PROJECTS_DIR}/quarkus",
    "commons-lang": f"{PROJECTS_DIR}/commons-lang",
    "jabref":       f"{PROJECTS_DIR}/jabref",
    "resilience4j": f"{PROJECTS_DIR}/resilience4j",
    "hibernate-orm":f"{PROJECTS_DIR}/hibernate-orm",
}

for name, project_path in project_paths.items():
    output_path = f"{OUTPUT_DIR}/{name}"

    if os.path.exists(f"{output_path}/class.csv"):
        print(f"[SKIP] {name} déjà analysé")
        continue

    os.makedirs(output_path, exist_ok=True)
    print(f"[CK] Analyse de {name}...")

    result = subprocess.run(
        [
            "java", "-jar", CK_JAR,
            project_path,
            "true",
            "0",
            "false",
            output_path + "/"
        ],
        capture_output=True, text=True,
        timeout=300
    )

    if result.returncode == 0:
        print(f"[OK] {name}")
    else:
        print(f"[ERREUR] {name} : {result.stderr[:300]}")