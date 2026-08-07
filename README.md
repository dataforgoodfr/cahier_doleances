# Cahiers de doléances

Projet Data For Good : Outil de découverte, visualisation et annotation des thèmes abordés dans des cahiers de doléances.
Les contributions extraites des PDF sont stockées en base PostgreSQL ; une app Gradio permet
de les parcourir commune par commune et de les annoter (anonymisé, contribution d'intérêt).

## Organisation

- `database/` : le modèle de données et les migrations qui structurent la base PostgreSQL | [documentation](database/README.md)
- `extraction/` : les pipelines d'extraction de texte depuis les PDFs
  - `extraction/without_ocr/` : extraction du texte natif, sans OCR | [documentation](extraction/without_ocr/README.md)
- `gradio_app/` : l'interface pour parcourir les contributions et les annoter | [documentation](gradio_app/README.md)
- `topic-builder/` : l'utilitaire de découverte, structuration et annotation des thèmes abordés dans les contributions | [documentation](topic-builder/README.md)

## Installation

Ce projet utilise [uv](https://docs.astral.sh/uv/) pour la gestion des dépendances Python
(prérequis). Une fois uv installé :

```bash
uv sync
```

Cela installe la bonne version de Python, crée l'environnement virtuel et installe les
dépendances. Sous VSCode l'environnement s'active automatiquement ; sinon :

```bash
source .venv/bin/activate
```

Ou préfixez vos commandes par `uv run` :

```bash
uv run python -m database.seed_mock # remplit la base avec le seed de démo
uv run python gradio_app/app.py # lance l'app
```

## Base de données

La connexion PostgreSQL est lue depuis `.env` (`DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME`). Voir [database/README.md](database/README.md) pour le modèle,
les migrations Alembic et le seed.

## Extraction des PDFs

Le module `extraction/without_ocr/` extrait le texte natif des PDFs page par page, le
stocke dans la table `page_extraction`, et calcule un score de qualité qui permet de
détecter les pages manuscrites. Le détail du pipeline et les commandes sont dans
[extraction/without_ocr/README.md](extraction/without_ocr/README.md).

### Lancer l'extraction

```bash
# 1. Renseigner la base de données et le dossier des PDFs dans .env
#    (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, PATH_TO_DATA)
# 2. Appliquer les migrations (notamment la table page_extraction)
uv run alembic upgrade head
# 3. Extraire tous les PDFs du dossier PATH_TO_DATA
uv run python -m extraction.without_ocr
```

Le script parcourt tous les PDFs de `PATH_TO_DATA`, extrait chaque page et la persiste
en base. Les PDFs déjà extraits sont ignorés (supprimer les rows existants pour
ré-extraire). À la fin il affiche un récapitulatif : nombre de PDFs traités, échecs
éventuels et identifiants des contributions créées.

## Qualité et sécurité du code (pre-commit)

Les hooks [pre-commit](https://pre-commit.com/) tournent à chaque commit, et la CI
les rejoue sur chaque PR (`.github/workflows/pre-commit.yaml`). Trois familles :

- **hygiène** : espaces/fins de ligne, newline final, syntaxe YAML, résidus de merge ;
- **lint Python** : ruff avec autofix ;
- **sécurité** : [gitleaks](https://github.com/gitleaks/gitleaks) bloque tout secret
  (mot de passe, clé API, token) avant qu'il parte dans un repo public, et
  `check-added-large-files` refuse les fichiers > 500 Ko (dump, PDF égaré).

```bash
uv run pre-commit install # une fois : active les hooks à chaque commit
uv run pre-commit run --all-files # lancer manuellement sur tout le repo
uv run pre-commit autoupdate # mettre à jour les versions des hooks
```

## Tester avec Tox

```bash
tox -vv
```
