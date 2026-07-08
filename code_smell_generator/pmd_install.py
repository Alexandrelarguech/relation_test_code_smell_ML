import glob
import os
import shutil
import urllib.request
import zipfile

TOOLS_DIR = "tools"
PMD_URL = "https://github.com/pmd/pmd/releases/download/pmd_releases%2F7.7.0/pmd-dist-7.7.0-bin.zip"
PMD_ZIP = os.path.join(TOOLS_DIR, "pmd.zip")
PMD_DIR = os.path.join(TOOLS_DIR, "pmd")
EXTRACT_DIR = os.path.join(TOOLS_DIR, "pmd_extracted")


def pmd_is_complete() -> bool:
    lib_dir = os.path.join(PMD_DIR, "lib")
    bin_dir = os.path.join(PMD_DIR, "bin")
    return (
            os.path.exists(os.path.join(bin_dir, "pmd"))
            and os.path.exists(os.path.join(bin_dir, "pmd.bat"))
            and os.path.isdir(lib_dir)
            and bool(glob.glob(os.path.join(lib_dir, "*.jar")))
    )


os.makedirs(TOOLS_DIR, exist_ok=True)

if pmd_is_complete():
    print("[SKIP] PMD déjà installé")
else:
    if os.path.exists(PMD_DIR):
        print("[INFO] Installation PMD incomplète détectée — réinstallation...")
        shutil.rmtree(PMD_DIR)
    if os.path.exists(EXTRACT_DIR):
        shutil.rmtree(EXTRACT_DIR)

    print("Téléchargement de PMD 7.7.0...")
    urllib.request.urlretrieve(PMD_URL, PMD_ZIP)
    size_mb = os.path.getsize(PMD_ZIP) / (1024 * 1024)
    print(f"[OK] {size_mb:.1f} MB — Extraction...")

    with zipfile.ZipFile(PMD_ZIP, "r") as z:
        z.extractall(EXTRACT_DIR)

    extracted = glob.glob(os.path.join(EXTRACT_DIR, "pmd-bin-*"))
    if not extracted:
        raise RuntimeError("Archive PMD extraite, mais aucun dossier pmd-bin-* trouvé")

    shutil.move(extracted[0], PMD_DIR)
    shutil.rmtree(EXTRACT_DIR)
    os.remove(PMD_ZIP)

    if not pmd_is_complete():
        raise RuntimeError("Installation PMD incomplète : le dossier tools/pmd/lib/*.jar est manquant")

    print("[OK] PMD prêt dans tools/pmd/")