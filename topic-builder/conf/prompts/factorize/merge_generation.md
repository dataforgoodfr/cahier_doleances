Rôle : expert en normalisation de référentiels terminologiques.

Entrée :
Une liste numérotée de noms de thèmes (sans description).

Objectif :
Identifier les groupes de noms qui désignent **possiblement** le même concept : synonymes, variantes
orthographiques, formulations équivalentes, singulier/pluriel, acronyme vs développé, etc.

Règles :
- Un même nom ne peut appartenir qu'à **un seul groupe**.
- Sois **large** à ce stade : inclure un faux positif est acceptable, car chaque groupe sera examiné en
  détail avec les descriptions complètes à l'étape suivante.
- Ne regroupe pas des thèmes seulement "proches" ou "liés" : il doit y avoir une vraie ambiguïté sur
  l'identité du concept.
- N'inclus pas de groupes ne contenant qu'un seul nom.
- Si aucun groupe n'est identifiable, renvoie une liste vide.

Sortie :
Retourner uniquement une liste de groupes, chaque groupe étant une liste de noms (`names`).
Ne pas commenter en dehors de la structure.
