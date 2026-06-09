import urllib.request, zipfile, os, glob, shutil

os.makedirs("../tools", exist_ok=True)

pmd_url = "https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.7.0/pmd-dist-7.7.0-bin.zip"
pmd_zip = "tools/pmd.zip"
pmd_dir = "../tools/pmd"

if not os.path.exists(pmd_dir):
    print("Téléchargement de PMD 7.7.0...")
    urllib.request.urlretrieve(pmd_url, pmd_zip)
    size_mb = os.path.getsize(pmd_zip) / (1024 * 1024)
    print(f"[OK] {size_mb:.1f} MB — Extraction...")
    with zipfile.ZipFile(pmd_zip, "r") as z:
        z.extractall("tools/pmd_extracted")
    extracted = glob.glob("tools/pmd_extracted/pmd-bin-*")
    if extracted:
        shutil.move(extracted[0], pmd_dir)
        print("[OK] PMD prêt dans tools/pmd/")
    os.remove(pmd_zip)
else:
    print("[SKIP] PMD déjà installé")