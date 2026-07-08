# Template DataForGood

This file will become your README and also the index of your
documentation.

# Contributing


## Installation

- [Installation de Python](#installation-de-python)

Ce projet utilise [uv](https://docs.astral.sh/uv/) pour la gestion des dépendances Python. Il est préréquis pour l'installation de ce projet.

Une fois installé, il suffit de lancer la commande suivante pour installer la version de Python adéquate, créer un environnement virtuel et installer les dépendances du projet.

```bash
uv sync
```

A l'usage, si vous utilisez VSCode, l'environnement virtuel sera automatiquement activé lorsque vous ouvrirez le projet. Sinon, il suffit de l'activer manuellement avec la commande suivante :

```bash
source .venv/bin/activate
```

Ou alors, utilisez la commande `uv run ...` (au lieu de `python ...`) pour lancer un script Python. Par exemple:

```bash
uv run pipelines/run.py run build_database
```

### Organisation en workspace

Le projet est structuré comme un [workspace uv](https://docs.astral.sh/uv/concepts/projects/workspaces/) : il se compose de plusieurs parties semi-indépendantes, chacune avec son propre `pyproject.toml` et sa propre liste de dépendances, mais partageant un unique fichier de verrouillage (`uv.lock`) à la racine. Cela garantit des versions cohérentes entre toutes les parties.

Les membres du workspace sont déclarés à la racine dans `pyproject.toml` :

```toml
[tool.uv.workspace]
members = ["db_schema"]
```

Membres actuels :

- **`db_schema`** — schéma SQLModel, moteur de connexion et migrations Alembic de la base Postgres des cahiers (dépendances : `sqlmodel`, `alembic`, `psycopg`).

Attention : par défaut, `uv sync` n'installe que les dépendances du membre **racine** (`pyproject.toml` à la racine). Les dépendances d'un membre du workspace (par exemple `db_schema`) ne sont pas installées automatiquement. Le fichier de verrouillage `uv.lock`, lui, couvre toujours l'ensemble du workspace.

Pour installer les dépendances des membres :

```bash
uv sync --all-packages          # racine + tous les membres du workspace
uv sync --package db_schema      # racine + le membre db_schema uniquement
```

Pour agir sur un membre précis :

```bash
# Ajouter une dépendance à un membre uniquement
uv add --package db_schema <paquet>

# Lancer une commande dans le contexte d'un membre
uv run --package db_schema alembic -c db_schema/alembic.ini upgrade head
```


## Lancer les precommit-hook localement

[Installer les precommit](https://pre-commit.com/)

    pre-commit run --all-files

## Utiliser Tox pour tester votre code

    tox -vv
