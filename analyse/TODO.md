# TODO — dataviz topics & intégration

Suites à donner au POC `simulation_graph_v2.py` (données v3, 8 niveaux).
État actuel : deux versions côte à côte pour comparatif —
`simulation_graph.py` (ancien, 4 niveaux, référence) et
`simulation_graph_v2.py` (nouveau, 8 niveaux, dynamique).

---

## 1. Améliorer la dataviz — structure des graphes

**Couleurs**
- [ ] Valider la rampe par niveau (0 feuille → 7 racine) vs les 4 couleurs franches de l'ancien.
- [ ] Décider : couleur = **niveau** (profondeur) ou couleur = **branche** (grande famille) ?
      Colorer par branche rendrait les grands thèmes lisibles d'un coup d'œil.
- [ ] Vérifier le rendu en thème sombre (contraste de la rampe).

**UX navigation**
- [ ] Valider le modèle **dynamique** (racine → descendre/remonter) vs cascade fixe.
- [ ] Fil d'Ariane **cliquable** pour remonter à n'importe quel niveau du chemin.
- [ ] Densité de la vue d'ensemble : ajuster le défaut de « Profondeur d'aperçu »
      (le niveau ≥ 3 peut être chargé — tester ≥ 4 par défaut ?).
- [ ] Recherche par nom de topic (accès direct sans dérouler l'arbre).

---

## 2. Graphe sélectionnable (clic sur les nœuds)

Aujourd'hui la sélection passe **uniquement par les dropdowns** : le clic sur un
nœud Plotly n'est pas branché (limite Gradio).

- [ ] Brancher l'événement de sélection Plotly → nœud cliqué devient le focus.
      Piste : `gr.Plot(...).select(fn, ...)` (à tester selon version Gradio).
- [ ] Alternative si trop fragile : composant graphe JS custom
      (cytoscape.js / vis-network) intégré via `gr.HTML`.
- [ ] Objectif : cliquer un nœud = zoomer dedans, comme dans la viz de JB.

---

## 3. Intégration des données & consolidation du code

Cible : **supprimer `analyse/`**, brancher la vue topic sur la **base**, et
tout rassembler dans `gradio_app/`.

**Données → base**
- [ ] Décider avec l'équipe : qui charge la taxonomie en base (périmètre ownership).
- [ ] Migration additive de la table `topic` : ajouter `external_id` (UUID de JB),
      `description`, `level`. `parent` devient une FK auto-référente par `external_id`.
- [ ] Script de chargement **idempotent** (upsert par `external_id`) lisant `analysis_v3/`.
      Cf. règle « un référentiel se synchronise, il ne se vide pas ».
- [ ] Charger les `instance` (verbatim + summary + `is_literal`).
- [ ] Tester sur un **Postgres local Docker** avant Scaleway.

**Code → gradio_app/**
- [ ] Déplacer la logique de `simulation_graph_v2.py` en vue Gradio :
      `gradio_app/views/topic_graph.py` lisant la **base** (plus les fichiers).
- [ ] Requêtes hiérarchiques via `WITH RECURSIVE` (garde-fous profondeur + visités).
- [ ] Réutiliser `data_helpers.py` (engine partagé), pas de reconstruction en mémoire.
- [ ] Supprimer `analyse/` (fichiers bruts, notebooks, POC) une fois la vue en base OK.

**À ne pas perdre en migrant**
- [ ] La distinction **propre** (relié, sans cycle) — quasi inutile en v3 (11 isolés, 0 cycle),
      mais garder le garde-fou anti-cycle dans les requêtes récursives.
- [ ] Le calcul des **détections agrégées** par sous-arbre (récursif).
- [ ] Le filtre `is_literal` sur les verbatims (guillemets vs reformulé).

---

## Notes / dette

- [ ] Régénérer `topic_choices.ipynb` et l'artifact de réunion sur la **v3**
      (les chiffres actuels — 4 niveaux, 3709 propres, 8 arbres complets — sont périmés).
- [ ] Confirmer avec JB que `dataset.csv` (réutilisé de la v1) correspond bien au corpus v3.
- [ ] `analysis_v3.zip` (15 Mo) et `analysis_v3/` sont volumineux → vérifier `.gitignore`
      (ne pas committer les données brutes).
