# Base de données : modèle et fonctionnement

## Le modèle

```mermaid
erDiagram
    contribution ||--o{ extraction : "contribution_id"
    contribution ||--o{ page_extraction : "contribution_id"
    contribution ||--o{ instance : "contribution_id"
    topic ||--o{ instance : "topic_id"
    topic ||--o{ topic : "parent_id"
    contribution ||--o{ feeling : "contribution_id"
    contribution ||--o| annotation : "contribution_id"

    contribution {
        int id PK
        string city "parsée du nom du fichier"
        string pdf_file
        int start_page
        int end_page
        bool is_handwritten
    }
    extraction {
        int id PK
        int contribution_id FK
        string ocr "modèle qui a produit le texte"
        string text
        int num_words
        int num_lines
    }
    page_extraction {
        int id PK
        int contribution_id FK
        string pdf_name
        int page_number
        text text
        float quality_score "0.0 illisible à 1.0 propre"
        bool needs_ocr "page manuscrite suspectée"
        string city
    }
    topic {
        int id PK
        string external_id UK "UUID de la livraison analyse"
        string name
        text description
        int level "rang d'abstraction fourni par l'analyse"
        bool validated "relecture humaine"
        int parent_id FK "thème englobant ; NULL = racine"
        text parent "ancien parent par nom, à supprimer"
    }
    instance {
        int id PK
        int contribution_id FK "NULL tant que le lien doc n'est pas résolu"
        string external_doc_id "id du document dans la livraison"
        int topic_id FK
        text verbatim "extrait exact qui porte le thème"
        text summary "justification de la détection"
    }
    feeling {
        int id PK
        int contribution_id FK
        string name
    }
    annotation {
        int contribution_id PK, FK
        bool is_anonymized
        bool is_of_interest
    }
```

| Table | Contenu | Owner |
|---|---|---|
| `contribution` | métadonnées : commune, fichier, pages, manuscrit | équipe séparation |
| `extraction` | texte extrait une ligne par essai d'OCR | équipe extraction |
| `page_extraction` | texte extrait page par page (OCR-free) avec score de qualité et flag `needs_ocr` | équipe extraction |
| `topic` | taxonomie des thèmes, hiérarchie via `parent_id` | équipe analyse |
| `instance` | détections de thèmes : verbatim + justification, une ligne par détection | équipe analyse |
| `feeling` | sentiments détectés : une ligne par résultat | équipe analyse |
| `annotation` | variables activées dans l'app ("Anonymisé", "d'intérêt") | outil Gradio |

**La logique** : une tâche métier = une table, chaque équipe n'écrit que dans la sienne
(CR de réunion), et tout pointe vers `contribution.id`. **La pertinence** : aucune donnée
n'est écrite par deux équipes, et l'avancement se lit par l'existence des lignes (pas de
ligne `extraction` = pas encore extraite, pas de ligne `annotation` = pas encore annotée).

## Mettre à jour le modèle de données

La source de vérité est `database/models.py` ; Alembic versionne chaque évolution dans
`database/migrations/versions/` (committé, rejouable sur une base vierge).

Évolution **additive** (nouvelle colonne, nouvelle table) :

1. Modifier `database/models.py`
2. `uv run alembic revision --autogenerate -m "description"`
3. **Relire** le script généré dans `database/migrations/versions/`
4. `uv run alembic upgrade head`
5. Committer `models.py` + la migration

Évolution **destructive** (supprimer une colonne) : jamais en un coup — dump d'abord,
puis trois migrations *expand → backfill → contract* avec vérification chiffrée avant
le contract (voir les migrations du passage aux instances de topics comme exemple :
`expand ref_topic` → `backfill topic.name` → `contract suppression de topic.name`).

**Renommage** (table ou colonne) : `--autogenerate` ne le détecte pas — il générerait un
`drop` + `create` destructeur. On écrit la migration à la main avec `op.rename_table` /
`op.alter_column(new_column_name=…)`, qui préservent données, index et FK (voir la
migration `rename : topic -> instance, ref_topic -> topic`).

L'autogenerate crée les contraintes avec le nom `None`, ce qui rend le `downgrade`
inapplicable : les nommer à la main (`op.create_unique_constraint("uq_...", ...)`).

Ne pas reformater une migration déjà appliquée : c'est une archive, la retoucher
ne produit que du bruit dans les diffs et des conflits de merge.

La connexion est construite par `database/db.py` depuis `.env` (ou `DATABASE_URL`
pour un SQLite local) — jamais de credentials dans un fichier committé.

## Charger la livraison de l'équipe analyse

`database/load_analysis.py` lit `analyse/analysis_v4/` (`taxonomy.json` +
`instances.json`) et remplit `topic` et `instance`. Idempotent : les topics sont
synchronisés par `external_id` (un référentiel ne se vide pas), les instances
sont remplacées à chaque exécution.

Deux points à connaître :

- La livraison contient des **caractères NUL** que PostgreSQL refuse en `text` ;
  ils sont retirés au chargement, des deux côtés de la jointure par nom.
- Le rapprochement document → contribution n'est pas résolu (3441 contributions
  pour 1524 documents livrés). `contribution_id` reste NULL, l'identifiant source
  est conservé dans `external_doc_id` pour pouvoir faire le lien plus tard.

## Commandes

```bash
uv run alembic revision --autogenerate -m "..." # générer une migration
uv run alembic upgrade head # appliquer à la base
uv run alembic current # version actuelle de la base
uv run alembic check # écart entre models.py et la base
uv run python -m database.seed_mock # seed de démo : 4 contributions dactylographiées réelles
uv run python -m database.load_analysis # charger la livraison analyse
```

Dump avant toute évolution destructive (les dumps existants sont dans `backups/`) :

```bash
set -a; . ./.env; set +a
PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom --no-owner --no-privileges \
  --file="database/backups/${DB_NAME}_$(date +%F).dump"
```
