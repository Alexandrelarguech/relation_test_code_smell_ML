## 0. Pré-requis

- Python 3 installé.
- Java installé, car CK, PMD et TestSmellDetector sont lancés avec des fichiers `.jar` ou des scripts Java.
- Git installé pour cloner les projets open source.
- Dépendances Python utilisées par certains scripts, notamment `pandas` pour le nettoyage des CSV PMD.

Commande utile :

```bash
pip install pandas
```

## 1. Télécharger les outils d'analyse

### 1.1 Installer CK

CK sert à extraire des métriques orientées objet comme `wmc`, `dit`, `cbo`, `rfc`, `lcom` ou `loc`.

```bash
python project_collector/ck_install.py
```

Sortie attendue :

```text
tools/ck.jar
```

### 1.2 Installer PMD

PMD sert à détecter les code smells dans les classes de production.

```bash
python code_smell_generator/pmd_install.py
```

Sortie attendue :

```text
tools/pmd/
```

### 1.3 Installer TestFileDetector et TestSmellDetector

Ces deux outils servent à détecter les fichiers de test puis à extraire les test smells.

```bash
python test_smell_generator/jnose_install.py
```

Sorties attendues :

```text
tools/TestFileDetector.jar
tools/TestSmellDetector.jar
```

## 2. Cloner les projets open source

Le script `project_collector/clone_projects.py` contient la liste initiale des dépôts GitHub à cloner : Spring Boot, Quarkus, Commons Lang, JabRef, Resilience4j et Hibernate ORM.

Commande :

```bash
python project_collector/clone_projects.py
```

Algorithme :

1. créer le dossier `dataset/projects` si nécessaire ;
2. parcourir la liste des dépôts GitHub configurés ;
3. calculer le nom local du projet depuis le nom du dépôt ;
4. ignorer un projet déjà cloné ;
5. cloner le dépôt avec `git clone --depth=1` pour éviter de télécharger tout l'historique Git.

Sortie attendue :

```text
dataset/projects/<nom-du-projet>/
```

## 3. Extraire les métriques CK

Cette étape est optionnelle pour le dataset final code smell / test smell, mais elle peut enrichir le dataset ML avec des métriques de classes.

Commande :

```bash
python project_collector/extract_metrics.py
```

Algorithme :

1. parcourir les projets configurés dans `project_paths` ;
2. ignorer un projet si `dataset/metrics/<projet>/class.csv` existe déjà ;
3. lancer CK avec `java -jar tools/ck.jar` ;
4. écrire les métriques dans `dataset/metrics/<projet>/`.

Sortie principale attendue :

```text
dataset/metrics/<projet>/class.csv
```

Commande de vérification :

```bash
python project_collector/verify_metrics.py
```

## 4. Générer les code smells avec PMD

Le script PMD applique une liste de règles de design Java : `GodClass`, `ExcessiveClassLength`, `ExcessiveMethodLength`, `ExcessiveParameterList`, `TooManyFields`, `TooManyMethods`, `CyclomaticComplexity` et `CouplingBetweenObjects`.

Commande :

```bash
python code_smell_generator/codeSmell.py
```

Algorithme :

1. parcourir les projets configurés ;
2. choisir le dossier source à analyser pour chaque projet ;
3. ignorer un projet si `dataset/code_smells/<projet>.csv` existe déjà ;
4. lancer PMD en sortie CSV ;
5. écrire un CSV de violations par projet.

Sortie attendue :

```text
dataset/code_smells/<projet>.csv
```

## 5. Nettoyer les code smells pour retirer les tests

Cette étape supprime des CSV PMD les lignes correspondant à des fichiers situés dans un chemin de test, afin de garder les code smells des classes de production.

Commande :

```bash
python code_smell_generator/csv_clean_test.py
```

Algorithme :

1. lire chaque CSV dans `dataset/code_smells` ;
2. chercher les lignes dont la colonne `File` contient `/test/` ou `\\test\\` ;
3. supprimer ces lignes ;
4. réécrire le CSV nettoyé au même emplacement.

Sortie attendue :

```text
dataset/code_smells/<projet>.csv
```

## 6. Détecter les fichiers de test

Cette étape prépare l'entrée de TestSmellDetector en listant les fichiers de test de chaque projet.

Commande :

```bash
python test_smell_generator/csv_generator.py
```

Algorithme :

1. parcourir les projets configurés ;
2. lancer `TestFileDetector.jar` sur `dataset/projects/<projet>` ;
3. récupérer le CSV généré par l'outil ;
4. le déplacer dans `dataset/tsdetect_input/<projet>.csv`.

Sortie attendue :

```text
dataset/tsdetect_input/<projet>.csv
```

## 7. Corriger le CSV d'entrée de TestSmellDetector

Le script `csv_fix.py` reformate les CSV de fichiers de test pour produire le format attendu par TestSmellDetector.

Commande :

```bash
python test_smell_generator/csv_fix.py
```

Algorithme :

1. lire `dataset/tsdetect_input/<projet>.csv` ;
2. récupérer la colonne `FilePath` ;
3. supprimer les doublons ;
4. ignorer les chemins inexistants ;
5. écrire un CSV corrigé dans `dataset/tsdetect_fixed/<projet>.csv`.

Sortie attendue :

```text
dataset/tsdetect_fixed/<projet>.csv
```

## 8. Générer les test smells

Cette étape lance TestSmellDetector sur les CSV corrigés.

Commande :

```bash
python test_smell_generator/testSmellDetector.py
```

Algorithme :

1. parcourir les projets configurés ;
2. ignorer un projet si `dataset/test_smells/<projet>.csv` existe déjà ;
3. lancer `java -jar tools/TestSmellDetector.jar dataset/tsdetect_fixed/<projet>.csv` ;
4. récupérer le fichier `Output_TestSmellDetection_*.csv` généré ;
5. le déplacer vers `dataset/test_smells/<projet>.csv`.

Sortie attendue :

```text
dataset/test_smells/<projet>.csv
```

## 9. Construire le dataset final apparié classe / classe de test

Cette étape utilise le script `dataset_transformer/build_paired_dataset.py`. Elle ne scanne pas `dataset/projects` : elle lit uniquement les CSV déjà générés dans `dataset/code_smells` et `dataset/test_smells`.

Commande recommandée :

```bash
python dataset_transformer/build_paired_dataset.py \
  --code-smells-dir dataset/code_smells \
  --test-smells-dir dataset/test_smells \
  --output-dir dataset/final
```

Algorithme :

1. lister les projets à partir des noms de CSV dans `dataset/code_smells` et `dataset/test_smells`, ou depuis `--projects` si l'option est fournie ;
2. lire le CSV de code smells du projet ;
3. regrouper les violations PMD par classe de production ;
4. lire le CSV de test smells du projet ;
5. retrouver la classe de production associée à chaque test à partir du chemin Java et du nom de fichier ;
6. regrouper les test smells par classe de production ;
7. construire des lignes contenant côte à côte la classe, le test associé, les compteurs de code smells et les indicateurs de test smells ;
8. écrire `dataset/final/<projet>.csv` ;
9. fusionner tous les projets dans `dataset/final/all_projects.csv`.

Sorties attendues :

```text
dataset/final/<projet>.csv
dataset/final/all_projects.csv
```

Pour limiter la génération à quelques projets :

```bash
python dataset_transformer/build_paired_dataset.py --projects spring-boot quarkus
```

## 10. Ordre complet des commandes

```bash
pip install pandas
python project_collector/ck_install.py
python code_smell_generator/pmd_install.py
python test_smell_generator/jnose_install.py
python project_collector/clone_projects.py
python project_collector/extract_metrics.py
python code_smell_generator/codeSmell.py
python code_smell_generator/csv_clean_test.py
python test_smell_generator/csv_generator.py
python test_smell_generator/csv_fix.py
python test_smell_generator/testSmellDetector.py
python dataset_transformer/build_paired_dataset.py \
  --code-smells-dir dataset/code_smells \
  --test-smells-dir dataset/test_smells \
  --output-dir dataset/final
```

## 11. Structure finale attendue

```text
dataset/
├── projects/                 # dépôts clonés, dossier lourd
├── metrics/                  # métriques CK
├── code_smells/              # CSV PMD nettoyés
├── tsdetect_input/           # CSV de fichiers de test détectés
├── tsdetect_fixed/           # CSV corrigés pour TestSmellDetector
├── test_smells/              # CSV de test smells
└── final/                    # dataset final apparié
    ├── <projet>.csv
    └── all_projects.csv
```

## 12. Colonnes principales du dataset final

Le dataset final contient notamment :

- `project` : nom du projet ;
- `class_key` : clé normalisée de la classe Java ;
- `class_name` : nom simple de la classe ;
- `class_file` : chemin du fichier de production ;
- `test_file` : chemin du fichier de test associé ;
- `has_code_smell` : indicateur binaire ;
- `code_smell_total` : nombre total de code smells détectés sur la classe ;
- `has_test_smell` : indicateur binaire ;
- `test_smell_total` : nombre total de test smells détectés ;
- `code_smell_<Rule>` : compteur par règle PMD ;
- `test_smell_<Colonne>` : indicateur ou compteur par test smell.
