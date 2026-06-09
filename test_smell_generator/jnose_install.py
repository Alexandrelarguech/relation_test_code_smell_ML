import urllib.request, os

os.makedirs("../tools", exist_ok=True)

tools = {
    "tools/TestFileDetector.jar": "https://github.com/TestSmells/TestFileDetector/releases/download/v1.0/TestFileDetector.jar",
    "tools/TestSmellDetector.jar": "https://github.com/TestSmells/TestSmellDetector/releases/download/v2.0/TestSmellDetector.jar",
}

for dest, url in tools.items():
    if os.path.exists(dest):
        print(f"[SKIP] {dest} déjà présent")
        continue
    print(f"Téléchargement {dest}...")
    urllib.request.urlretrieve(url, dest)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"[OK] {size_mb:.1f} MB")