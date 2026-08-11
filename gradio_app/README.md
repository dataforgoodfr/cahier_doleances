# App Gradio : visualisation et annotation

Interface à deux onglets : **Par commune**  parcourir les contributions (texte extrait +
PDF source) et activer deux variables par contribution (**Anonymisé**, **Contribution
d'intérêt**)  et **Par thème**  consulter, en lecture seule, toutes les instances d'un
thème : KPI (instances / contributions / communes), grille de cartes (document source,
verbatim, résumé, sentiment) et répartition des thèmes sur tout le corpus.

## Fonctionnement

Les données sont lues **directement dans la base PostgreSQL**, pas de fichier intermédiaire.

**Par commune** : une contribution affiche ses thèmes (instances `topic` reliées au
référentiel `ref_topic`, avec verbatim et résumé quand l'analyse existe), ses sentiments
(`feeling`), le texte de sa dernière extraction (`extraction`, `max(id)`), et son PDF
(`data/raw/pdfs/`). Les deux cases cochées sont écrites dans la table `annotation`
(UPSERT ; les deux décochées = ligne supprimée).

**Par thème** : le dropdown liste la taxonomie `ref_topic` (avec le nombre d'instances,
y compris à 0) ; chaque instance devient une carte reconstruite via `@gr.render`.
Aucune écriture depuis cette vue. Voir `database/README.md` pour le modèle.

| Fichier | Rôle |
|---|---|
| `app.py` | coquille : assemble les onglets, charge le CSS, lance l'app |
| `views/commune.py` | onglet « Par commune » : navigation + annotation |
| `views/topic.py` | onglet « Par thème » : KPI + cartes + répartition (lecture seule) |
| `views/style.css` | styles des vues custom (classes `tv-*`), chargé via `css_paths` |
| `data_helpers.py` | requêtes SQL (SQLAlchemy + pandas) et sauvegarde des annotations |


Deux interfaces sur un seul serveur :

    /          les onglets Gradio (par commune, par topic)
    /graphe    la vue graphe des thèmes, page maison

Le graphe ne peut pas être un onglet Gradio : `gr.Plot` n'expose pas
d'évènement de clic, or on veut naviguer en cliquant les nœuds. On sert donc
notre propre page, et le Blocks est monté sur la même FastAPI.

## Prérequis

1. Base accessible et remplie  via `uv run python -m database.seed_mock` (démo) ou le pipeline data.
2. `.env` renseigné : `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` (mêmes variables que `database/db.py`).
3. Les PDF présents dans `data/raw/pdfs/` pour l'aperçu (sinon « PDF introuvable » s'affiche, le reste marche).

## Lancer

```bash
uv run python gradio_app/app.py # http://localhost:7860
```
