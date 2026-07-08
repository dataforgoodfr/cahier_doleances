# db_schema

Schéma **SQLModel**, moteur de connexion et migrations **Alembic** de la base
Postgres des *cahiers de doléances*. Ce dossier est un membre du
[workspace uv](../README.md#organisation-en-workspace) et possède sa propre
liste de dépendances (`sqlmodel`, `alembic`, `psycopg`).

## Structure

| Fichier | Rôle |
| --- | --- |
| `models.py` | Modèles SQLModel (tables `contribution`, `city`, `pdf`, `topic`, `feeling`, …) et leurs relations. |
| `database.py` | Création du moteur et fabrique de sessions. |
| `alembic.ini` | Configuration Alembic. |
| `migrations/` | Scripts de migration Alembic (`env.py`, `versions/`). |

## Configuration

La chaîne de connexion est lue depuis la variable d'environnement
`DATABASE_URL`, avec un repli sur une instance Postgres locale :

```bash
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/cahiers"
```

## Installation

Depuis la racine du projet :

```bash
uv sync --package db_schema
```

## Migrations

Les changements de schéma sont gérés par Alembic — `database.py` n'appelle
volontairement pas `create_all`.

```bash
# Appliquer les migrations jusqu'à la dernière version
uv run --package db_schema alembic -c db_schema/alembic.ini upgrade head

# Générer une migration à partir des modifications de models.py
uv run --package db_schema alembic -c db_schema/alembic.ini revision --autogenerate -m "description"
```

## Prototypage rapide avec SQLite

Pour explorer le schéma sans Postgres (tests, prototypage), on peut créer une
base SQLite locale directement à partir des modèles avec `create_all`. Utile
uniquement pour du jetable : contrairement à Alembic, `create_all` ne crée que
les tables manquantes et ne gère pas l'évolution du schéma.

```python
from sqlmodel import Session, SQLModel, create_engine

import db_schema.models  # enregistre toutes les tables sur SQLModel.metadata
from db_schema.models import City, Contribution

# Base SQLite dans un fichier (ou "sqlite://" pour une base en mémoire)
engine = create_engine("sqlite:///cahiers.db", echo=True)

# Crée toutes les tables définies dans models.py
SQLModel.metadata.create_all(engine)

# Insertion d'un exemple
with Session(engine) as session:
    paris = City(name="Paris", insee="75056", department="75")
    session.add(Contribution(text="Un exemple de doléance.", city=paris))
    session.commit()
```

```bash
uv run --package db_schema python chemin/vers/le_script.py
```

## Utilisation dans le code

```python
from db_schema.database import get_session
from db_schema.models import Contribution

with get_session() as session:
    session.add(Contribution(text="…"))
    session.commit()
```
