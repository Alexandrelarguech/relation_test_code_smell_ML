import subprocess
import os

projects = [
    "spring-projects/spring-boot",
    "quarkusio/quarkus",
    "apache/commons-lang",
    "JabRef/jabref",
    "resilience4j/resilience4j",
    "hibernate/hibernate-orm",
]

os.makedirs("../dataset/projects", exist_ok=True)

for proj in projects:
    name = proj.split("/")[1]
    dest = f"dataset/projects/{name}"
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