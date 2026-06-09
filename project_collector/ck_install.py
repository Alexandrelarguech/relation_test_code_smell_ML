import urllib.request
import os

ck_url = "https://repo1.maven.org/maven2/com/github/mauricioaniche/ck/0.7.0/ck-0.7.0-jar-with-dependencies.jar"
ck_jar = "tools/ck.jar"

os.makedirs("../tools", exist_ok=True)

print("Téléchargement de CK depuis Maven Central...")
urllib.request.urlretrieve(ck_url, ck_jar)

size_mb = os.path.getsize(ck_jar) / (1024 * 1024)
print(f"[OK] CK téléchargé — taille : {size_mb:.1f} MB")

if size_mb < 5:
    print("[ATTENTION] Fichier trop petit, quelque chose a mal tourné")
else:
    print("[PRÊT] Tu peux lancer extract_metrics.py")