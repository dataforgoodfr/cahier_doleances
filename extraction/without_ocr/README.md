# Extraction sans OCR

Extrait le texte natif contenu dans les PDFs des cahiers de doléances, sans passer
par un OCR. Pour chaque fichier PDF :

- les **2 premières pages** sont lues comme des pages de metadata (ville, code INSEE)
  et ne sont pas persistées en base ;
- à partir de la page 3, chaque page est extraite, nettoyée et stockée dans la table
  `page_extraction` ;
- l'extraction s'arrête dès qu'on rencontre le marqueur `Fin des pages écrites` ;
- la ville est extraite via une regex sur le texte des pages de metadata et stockée
  dans `contribution.city` et `page_extraction.city` ;
- un **score de qualité** (`quality_score`, entre 0 et 1) est calculé avec `wordfreq`
  pour mesurer la proportion de mots français courants. Si le score est faible, la
  page est probablement manuscrite ou de mauvaise qualité : elle est alors flagguée
  `needs_ocr = True` et le champ `contribution.is_handwritten` est mis à jour.

Le modèle de données (`contribution`, `page_extraction`) est documenté dans
[database/README.md](../../database/README.md).

## Organisation

| Fichier           | Rôle                                                                     |
| ----------------- | ------------------------------------------------------------------------ |
| `config.py`       | paramètres métier de l'extraction (marqueur de fin, seuils, regex ville) |
| `settings.py`     | configuration lue depuis `.env` (`PATH_TO_DATA`, `LOG_LEVEL`) et logger  |
| `discovery.py`    | découverte des PDFs dans le dossier de données                           |
| `extract_text.py` | extraction, nettoyage et scoring page par page                           |
| `persist.py`      | écriture en base (`contribution`, `page_extraction`)                     |
| `timing.py`       | décorateur `@timed` de mesure du temps d'exécution                       |
| `__main__.py`     | script d'extraction par lot                                              |
| `tests/`          | tests unitaires et d'intégration du module                               |

## Pré-requis

1. Renseigner la base de données dans `.env` (`DB_HOST`, `DB_PORT`, `DB_USER`,
   `DB_PASSWORD`, `DB_NAME`). S'assurer que la base est accessible et que les migrations ont été appliquées.
2. Renseigner le dossier contenant les PDFs dans `.env` :

```bash
PATH_TO_DATA=/chemin/vers/les/pdfs
```

## Lancer l'extraction

```bash
# Appliquer les migrations (notamment la table page_extraction)
uv run alembic upgrade head

# Extraire tous les PDFs du dossier PATH_TO_DATA
uv run python -m extraction.without_ocr
```

Le script affiche un récapitulatif final : nombre de PDFs traités, échecs éventuels
et identifiants des contributions créées en base.

## Tester

```bash
uv run --extra dev pytest extraction
```
