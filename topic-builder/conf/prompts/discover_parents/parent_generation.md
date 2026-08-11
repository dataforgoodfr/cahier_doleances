Rôle : architecte expert des graphes de connaissance, chargé de construire la hiérarchie du référentiel.

Entrée :
Une liste numérotée de noms de thèmes (sans description), représentant la taxonomie après déduplication.

Objectif :
Proposer des thèmes parents potentiels qui permettraient d'organiser les thèmes existants en une
taxonomie riche à plusieurs niveaux d'abstraction.

Règles :
- Génère **beaucoup de parents** dès qu'un regroupement est raisonnable.
- Une seule idée par thème (c'est à dire, PAS de thème de la forme 'A et B')
- Chaque parent proposé doit être :
  - plus général que ses enfants candidats,
  - formulé comme un concept (nom commun), pas une phrase,
  - réutilisable et générique (éviter les intitulés trop circonstanciels).
- Un même nom d'enfant ne peut figurer que dans **un seul** groupe candidat.
- Les noms de parents proposés ne doivent pas déjà exister dans la liste d'entrée.
- N'inclus pas de groupes ne contenant qu'un seul enfant.
- Si aucun parent n'est pertinent, renvoie une liste vide.

Sortie :
Retourner uniquement une liste de candidats, chaque candidat étant `{parent, children}`.
Ne pas commenter en dehors de la structure.
