# RapportEval pour Windows

**RapportEval** est une application de génération de rapports d'évaluation pédagogique à partir de fichiers Excel `.xlsx`. L'application calcule les statistiques localement, permet une interprétation assistée par l'API Albert, propose une étape de relecture, puis génère un rapport PowerPoint.

## Version disponible

Le workflow GitHub Actions produit actuellement le package :

```text
RapportEval-Windows-x64.zip
```

### Compatibilité

- Windows 10 64 bits, version 22H2 conseillée
- Windows 11 64 bits
- Architecture x86-64 / AMD64, pour les PC Intel et AMD

Cette version n'est pas destinée à Windows 32 bits. Elle n'est pas non plus construite comme une application ARM64 native.

## Téléchargement

Le package Windows est généré par le workflow :

```text
Build RapportEval Windows x64
```

Pour récupérer une construction :

1. ouvrir l'onglet **Actions** du dépôt ;
2. ouvrir une exécution réussie du workflow ;
3. sélectionner **Summary** ;
4. télécharger l'artefact **RapportEval-Windows-x64** dans la section **Artifacts** ;
5. décompresser l'archive téléchargée par GitHub ;
6. décompresser ensuite `RapportEval-Windows-x64.zip` si celui-ci se trouve dans la première archive.

> Pour une version destinée à être conservée et distribuée durablement, il est préférable de publier le ZIP dans une **GitHub Release** plutôt que de le commiter dans le dépôt.

## Contenu du package

Après extraction, le dossier de l'application doit notamment contenir :

```text
RapportEval/
├── RapportEval.exe
├── _internal/
└── Engine/
    ├── cli_generate.py
    ├── generate.js
    ├── logo_seatech.png
    └── node_modules/
```

**Ne déplacez pas `RapportEval.exe` seul.** Le fichier exécutable, le dossier `_internal` et le dossier `Engine` doivent rester ensemble.

Pour obtenir une icône sur le Bureau, créez un raccourci vers `RapportEval.exe` au lieu de déplacer l'exécutable.

## Prérequis de la version actuelle

Cette première version AMD64 n'embarque pas encore les exécutables Python et Node.js. Les composants ci-dessous doivent donc être installés sur le poste utilisateur.

### 1. Python 3.12 x64

Installez Python 3.12 pour Windows en version **64 bits x86-64 / AMD64**. Ne choisissez pas l'installeur ARM64.

Pendant l'installation, cochez si possible :

```text
Add python.exe to PATH
```

Vérifiez ensuite l'architecture dans PowerShell :

```powershell
python -c "import platform; print(platform.machine())"
```

Résultat attendu :

```text
AMD64
```

Depuis le dossier dans lequel RapportEval a été extrait, installez les bibliothèques nécessaires au moteur :

```powershell
python -m pip install --upgrade pip
python -m pip install -r .\Engine\requirements.txt
```

Les principales dépendances sont :

- pandas ;
- NumPy ;
- openpyxl ;
- OpenAI Python, utilisé pour l'API compatible Albert.

### 2. Node.js 22 LTS x64

Installez Node.js 22 LTS pour Windows en version x64.

Vérifiez l'installation dans PowerShell :

```powershell
node --version
```

Le dossier `Engine\node_modules` est déjà fourni dans le package. Il n'est donc normalement pas nécessaire d'exécuter `npm install` sur le poste utilisateur.

### 3. Microsoft Visual C++ Redistributable x64, si nécessaire

Si Windows signale une bibliothèque manquante telle que `VCRUNTIME140.dll` ou `MSVCP140.dll`, installez **Microsoft Visual C++ Redistributable 2015-2022 x64**, puis redémarrez Windows.

## Installation

1. Téléchargez et décompressez le package Windows.
2. Copiez le dossier complet `RapportEval` dans un emplacement permanent, par exemple :

```text
C:\Programmes_portables\RapportEval
```

ou :

```text
C:\Users\UTILISATEUR\Documents\RapportEval_Application
```

3. Conservez toute l'arborescence du package.
4. Lancez :

```text
RapportEval.exe
```

### Avertissement SmartScreen

Windows Defender SmartScreen peut signaler que l'application n'est pas reconnue, car l'exécutable n'est pas encore signé numériquement.

Ne choisissez **Informations complémentaires**, puis **Exécuter quand même**, que si :

- le fichier provient de ce dépôt ou d'une release officielle ;
- l'archive a été téléchargée depuis une source de confiance ;
- le SHA-256 correspond au fichier publié avec le package.

## Configuration du moteur

Dans RapportEval, ouvrez l'onglet **Albert et moteur**.

### Chemin Python

Exemple :

```text
C:\Users\UTILISATEUR\AppData\Local\Programs\Python\Python312\python.exe
```

Pour retrouver le chemin :

```powershell
where.exe python
```

### Chemin Node.js

Exemple :

```text
C:\Program Files\nodejs\node.exe
```

Pour retrouver le chemin :

```powershell
where.exe node
```

### Dossier Engine

Sélectionnez le dossier `Engine` placé à côté de `RapportEval.exe`, par exemple :

```text
C:\Programmes_portables\RapportEval\Engine
```

Cliquez ensuite sur **Vérifier le moteur**. Le diagnostic doit confirmer la présence de :

```text
Python
Node.js
cli_generate.py
generate.js
logo_seatech.png
package.json
module pptxgenjs
```

## Configuration de l'API Albert

Dans l'onglet **Albert et moteur** :

1. collez la clé API Albert ;
2. vérifiez l'URL de base ;
3. renseignez le modèle utilisé ;
4. enregistrez les paramètres.

URL de base habituelle :

```text
https://albert.api.etalab.gouv.fr/v1
```

La clé est stockée dans le gestionnaire d'identifiants Windows au moyen de `keyring`. Une vraie clé API ne doit jamais être ajoutée au dépôt GitHub, à un fichier partagé, à un rapport ou à une capture d'écran.

## Premier test

Après l'installation :

1. ouvrez RapportEval ;
2. lancez **Vérifier le moteur** ;
3. sélectionnez un fichier Excel `.xlsx` de test ;
4. renseignez le cours, la promotion, l'année universitaire et le nombre d'individus sollicités ;
5. lancez la préparation du rapport ;
6. relisez et corrigez les éléments proposés ;
7. générez le PowerPoint.

Le rapport final est normalement enregistré dans :

```text
C:\Users\UTILISATEUR\Documents\RapportEval
```

## Vérification du SHA-256

Le workflow fournit normalement le fichier :

```text
RapportEval-Windows-x64.sha256.txt
```

Pour vérifier l'archive dans PowerShell :

```powershell
Get-FileHash .\RapportEval-Windows-x64.zip -Algorithm SHA256
```

La valeur obtenue doit être identique à celle inscrite dans le fichier `.sha256.txt`.

## Dépannage

### RapportEval.exe ne démarre pas

- vérifiez que l'archive a été entièrement extraite ;
- conservez `_internal` à côté de `RapportEval.exe` ;
- essayez depuis un dossier utilisateur non protégé ;
- installez Microsoft Visual C++ Redistributable x64 si Windows signale une DLL manquante.

### Python est introuvable

```powershell
where.exe python
python -c "import platform; print(platform.machine())"
```

Renseignez le chemin complet de `python.exe` dans RapportEval. L'architecture attendue est `AMD64`.

### Une bibliothèque Python est introuvable

```powershell
python -m pip install -r .\Engine\requirements.txt
```

### Node.js est introuvable

```powershell
where.exe node
node --version
```

Renseignez le chemin complet de `node.exe` dans RapportEval.

### Le dossier Engine est introuvable

Sélectionnez le dossier `Engine` situé dans le même dossier que `RapportEval.exe`.

### pptxgenjs est introuvable

Vérifiez la présence de :

```text
Engine\node_modules\pptxgenjs
```

### Le PowerPoint n'est pas généré

- vérifiez Python, Node.js et Engine dans le diagnostic ;
- vérifiez les droits d'écriture dans `Documents\RapportEval` ;
- consultez le message d'erreur affiché par RapportEval.

## Construction automatique

Le workflow GitHub Actions :

```text
.github/workflows/build-windows-x64.yml
```

utilise un runner Windows AMD64, Python 3.12 x64, Node.js x64 et PyInstaller. Il produit :

```text
RapportEval-Windows-x64.zip
RapportEval-Windows-x64.sha256.txt
```

Les dossiers générés localement ne sont pas versionnés :

```text
.venv/
build/
dist/
Engine/node_modules/
__pycache__/
```

## Limitation actuelle et évolution prévue

L'application principale est bien compilée pour Windows AMD64, mais Python et Node.js doivent encore être installés séparément.

Une future version pourra embarquer :

```text
Runtime\python\python.exe
Runtime\node\node.exe
```

L'installation deviendra alors entièrement autonome.

