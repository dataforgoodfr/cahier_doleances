# App Gradio : visualisation et annotation

Deux interfaces sur un seul serveur :

    /          Par commune  parcourir les contributions (texte extrait + PDF) et
               activer deux variables (Anonymisé, Contribution d'intérêt)
    /graphe    Vue graphe des thèmes  explorer la taxonomie en cliquant les nœuds

Les données sont lues **directement dans la base PostgreSQL**, pas de fichier
intermédiaire. Les PDF viennent de l'Object Storage Scaleway.

## Fonctionnement

**Par commune** : une contribution affiche ses thèmes (`instance` reliées au
référentiel `topic`, avec verbatim et résumé quand l'analyse existe), ses
sentiments (`feeling`), le texte de sa dernière extraction (`extraction`,
`max(id)`) et son PDF. Les deux cases cochées sont écrites dans `annotation`
(UPSERT ; les deux décochées = ligne supprimée).

Les communes au nom vide sont écartées de la liste : le parsing du PDF échoue
parfois, ce qui ferait démarrer la vue sur une commune sans nom.

**Vue graphe** : la taxonomie et ses détections sont chargées une fois au
démarrage (6788 topics, 9579 instances) puis servies en JSON. Le graphe est une
page maison, pas un onglet Gradio : `gr.Plot` n'expose pas d'évènement de clic,
or on veut naviguer en cliquant les nœuds. Le Blocks est monté sur la même
FastAPI via `gr.mount_gradio_app`, après les routes du graphe pour que `/` ne
masque pas `/graphe`.

Les arbres sont rangés en **strates** par hauteur (A canopée, B sous-bois,
C semis) et la couleur donne la **distance à la racine**, pas le `level` de la
livraison. C'est un outil d'exploration, pas une représentation proportionnelle
du corpus : voir `analyse/structure_arbres_v3.ipynb` pour les biais assumés.

**PDF** : la base ne stocke que le nom du fichier, S3 le range sous un préfixe.
On construit l'index nom → clé au premier appel, puis on sert une **URL
présignée** (1 h). Le navigateur va chercher le fichier directement sur
Scaleway : certains PDF font 43 Mo, ils ne transitent pas par l'app. Repli sur
`data/raw/pdfs/` si le bucket est injoignable.

| Fichier | Rôle |
|---|---|
| `app.py` | assemble le Blocks, expose les routes du graphe, monte le tout |
| `views/commune.py` | vue « Par commune » : navigation + annotation |
| `views/graph.py` | vue graphe : strates, couleurs, layout, réponses JSON |
| `views/static/` | page du graphe (`index.html`, `style.css`, `app.js`) |
| `views/style.css` | styles du Blocks, chargé via `css_paths` |
| `data_helpers.py` | requêtes SQL (SQLAlchemy + pandas) et écriture des annotations |
| `s3_helpers.py` | index des PDF et URL présignées |

## Prérequis

1. Base accessible et remplie : `uv run python -m database.seed_mock` (démo) ou
   `uv run python -m database.load_analysis` (livraison analyse).
2. `.env` renseigné :
   - base : `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
   - PDF : `S3_ENDPOINT`, `S3_BUCKET_NAME`, `SCW_ACCESS_KEY`, `SCW_SECRET_KEY`
     (`S3_REGION` est déduite de l'endpoint si elle n'est pas renseignée)

Sans les variables S3, tout fonctionne sauf l'aperçu PDF.

## Lancer

```bash
uv run python gradio_app/app.py   # http://localhost:7860
```

## Limites connues

- La taxonomie est chargée au démarrage : recharger la base demande un
  redémarrage de l'app.
- `instance.contribution_id` est NULL : le rapprochement entre les documents de
  la livraison analyse et les contributions n'est pas résolu. La vue graphe
  affiche donc l'identifiant source (`doc 73`), et la vue commune n'affiche pas
  encore les thèmes détectés par l'équipe analyse.
