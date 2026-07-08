import os
import subprocess

PROJECTS_DIR = "dataset/projects"

projects = [
    # Projets initiaux
    "spring-projects/spring-boot",
    "quarkusio/quarkus",
    "apache/commons-lang",
    "JabRef/jabref",
    "resilience4j/resilience4j",
    "hibernate/hibernate-orm",

    # Projets supplémentaires proposés dans docs/open_source_projects_to_add.md
    "elastic/elasticsearch",
    "square/okhttp",
    "apache/dubbo",
    "google/guava",
    "mockito/mockito",
    "junit-team/junit5",
    "netty/netty",
    "apache/kafka",
    "apache/cassandra",
    "apache/pulsar",
]

os.makedirs(PROJECTS_DIR, exist_ok=True)

for proj in projects:
    name = proj.split("/")[1]
    dest = os.path.join(PROJECTS_DIR, name)
    url = f"https://github.com/{proj}.git"

    if os.path.exists(dest):
        print(f"[SKIP] {name} déjà cloné")
        continue

    print(f"[CLONE] {name}...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", url, dest],
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"[OK] {name}")
    else:
        print(f"[ERREUR] {name} :\n{result.stderr[:500]}")