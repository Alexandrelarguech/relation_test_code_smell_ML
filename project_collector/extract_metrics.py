import os
import subprocess

PROJECTS_DIR = "dataset/projects"
OUTPUT_DIR = "dataset/metrics"
CK_JAR = "tools/ck.jar"

project_paths = {
    # Projets initiaux
    "spring-boot": os.path.join(PROJECTS_DIR, "spring-boot"),
    "quarkus": os.path.join(PROJECTS_DIR, "quarkus"),
    "commons-lang": os.path.join(PROJECTS_DIR, "commons-lang"),
    "jabref": os.path.join(PROJECTS_DIR, "jabref"),
    "resilience4j": os.path.join(PROJECTS_DIR, "resilience4j"),
    "hibernate-orm": os.path.join(PROJECTS_DIR, "hibernate-orm"),

    # Projets supplémentaires proposés dans docs/open_source_projects_to_add.md
    "elasticsearch": os.path.join(PROJECTS_DIR, "elasticsearch"),
    "okhttp": os.path.join(PROJECTS_DIR, "okhttp"),
    "dubbo": os.path.join(PROJECTS_DIR, "dubbo"),
    "guava": os.path.join(PROJECTS_DIR, "guava"),
    "mockito": os.path.join(PROJECTS_DIR, "mockito"),
    "junit5": os.path.join(PROJECTS_DIR, "junit5"),
    "netty": os.path.join(PROJECTS_DIR, "netty"),
    "kafka": os.path.join(PROJECTS_DIR, "kafka"),
    "cassandra": os.path.join(PROJECTS_DIR, "cassandra"),
    "pulsar": os.path.join(PROJECTS_DIR, "pulsar"),
}

for name, project_path in project_paths.items():
    output_path = os.path.join(OUTPUT_DIR, name)

    if os.path.exists(os.path.join(output_path, "class.csv")):
        print(f"[SKIP] {name} déjà analysé")
        continue

    if not os.path.exists(project_path):
        print(f"[CHEMIN MANQUANT] {name} : {project_path}")
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
        timeout=1800
    )

    if result.returncode == 0:
        print(f"[OK] {name}")
    else:
        print(f"[ERREUR] {name} : {result.stderr[:300]}")