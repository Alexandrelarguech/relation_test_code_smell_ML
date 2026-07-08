import subprocess, os

PROJECTS_DIR = "dataset/projects"
OUTPUT_DIR   = "dataset/code_smells"
os.makedirs(OUTPUT_DIR, exist_ok=True)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PMD_CMD  = os.path.join(BASE_DIR, "..", "tools", "pmd", "bin", "pmd.bat")

RULES = ",".join([
    "category/java/design.xml/GodClass",
    "category/java/design.xml/ExcessiveClassLength",
    "category/java/design.xml/ExcessiveMethodLength",
    "category/java/design.xml/ExcessiveParameterList",
    "category/java/design.xml/TooManyFields",
    "category/java/design.xml/TooManyMethods",
    "category/java/design.xml/CyclomaticComplexity",
    "category/java/design.xml/CouplingBetweenObjects",
])

project_paths = {
    # Projets initiaux
    "spring-boot": os.path.join(PROJECTS_DIR, "spring-boot", "core"),
    "quarkus": os.path.join(PROJECTS_DIR, "quarkus", "core"),
    "commons-lang": os.path.join(PROJECTS_DIR, "commons-lang"),
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

for name, src_path in project_paths.items():
    output_csv = os.path.join(OUTPUT_DIR, f"{name}.csv")

    if os.path.exists(output_csv):
        print(f"[SKIP] {name}")
        continue

    if not os.path.exists(src_path):
        print(f"[CHEMIN MANQUANT] {name} : {src_path}")
        print(f"  Contenu de dataset/projects/{name}/ : {os.listdir(f'../dataset/projects/{name}/')[:8]}")
        continue

    print(f"[PMD] Analyse de {name} ({src_path})...")
    result = subprocess.run(
        [
            PMD_CMD, "check",
            "-d", src_path,
            "-R", RULES,
            "-f", "csv",
            "--no-fail-on-violation",
            "-r", output_csv
        ],
        capture_output=True, text=True,
        timeout=1800  # 30 min
    )

    if os.path.exists(output_csv):
        with open(output_csv, encoding="utf-8", errors="ignore") as f:
            count = sum(1 for _ in f) - 1
        print(f"[OK] {name} — {count} violations détectées")
    else:
        print(f"[ERREUR] {name} : {result.stderr[:300]}")