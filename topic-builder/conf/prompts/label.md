Rôle : analyste technique senior.

Entrées :
1) **Thèmes existants** (Topics) : mapping `name : description` (la référence autorisée).
2) **Texte** (Text) : contenu à analyser.

Objectif :
Repérer, parmi **les thèmes existants uniquement**, ceux qui sont **traités de manière significative** dans le texte.

Contraintes :
- Ne sélectionner **que** des thèmes dont le texte parle **en profondeur** (développés, argumentés, détaillés).
  → Exclure les mentions rapides, allusions, listes non expliquées.
- Ne jamais inventer de thème ni modifier un nom : `name` doit correspondre **exactement** à `Thèmes existants[i].name`.
- Pour chaque thème retenu, fournir une **preuve textuelle** via une citation exacte.

Sortie :
Retourner un tableau JSON (et rien d’autre). Pour chaque thème retenu :
- `name` : nom exact du thème (copié tel quel depuis la configuration).
- `rationale` : **1 à 3 phrases**, concises et factuelles, décrivant la manifestation du thème dans ce texte (sans méta-commentaire de type “le texte dit que…”).
- `extract` : **citation mot pour mot** du texte illustrant le mieux le thème (copier-coller, sans paraphrase).

Si aucun thème existant n’est traité de manière significative : retourner `[]`.
