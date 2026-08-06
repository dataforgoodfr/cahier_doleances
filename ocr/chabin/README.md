# Cahiers de doléances — édition Chabin

Scripts d'extraction des contributions à partir de l'[édition des cahiers de doléances
de Marie-Anne Chabin](https://www.marieannechabin.fr/edition-de-cahiers-doleances-2019/),
qui propose des transcriptions PDF des cahiers de Charente-Maritime (dép. 17).

## `download_chabin_pdfs.py`

Récupère la liste des cahiers et les PDF de transcription depuis le site.

1. Parse le tableau de la page d'édition : code INSEE, intercommunalité, commune,
   nombre d'habitants, de contributions et de mots, plus les liens vers les PDF de
   transcription.
2. Applique quelques corrections manuelles (nombres de contributions erronés sur le
   site, liens manquants pour La Rochelle) via `correct_results()`.
3. Écrit le tout dans `cahiers-chabin.json`.
4. Télécharge les PDF listés dans un répertoire local (les fichiers déjà présents sont
   ignorés, 5 s d'attente entre deux téléchargements).

```bash
python download_chabin_pdfs.py
```

Les chemins de sortie sont les constantes `DEFAULT_CAHIERS_JSON` et
`DEFAULT_CHABIN_PDF_DIR` en tête de fichier. Par défaut elles pointent dans `data/` à la
racine du dépôt (gitignoré) ; la variable d'environnement `CAHIERS_DATA_DIR` permet de
déplacer ce répertoire sans toucher au code.

### Sorties

**`DEFAULT_CAHIERS_JSON`** — une liste JSON, un objet par commune du tableau, dans
l'ordre de la page :

```json
[
  {
    "insee": "17300",
    "intercommunalite": "CA de La Rochelle",
    "commune": "La Rochelle",
    "habitants": 77205,
    "contributions": 331,
    "mots": 74000,
    "pdf_links": ["https://www.marieannechabin.fr/.../...-1sur5-transcription.pdf"],
    "pdf_file": ["Cahier-de-doleances-de-La-Rochelle-1sur5-transcription.pdf"]
  }
]
```

Une commune sans transcription publiée a `pdf_links` et `pdf_file` vides.
 Un cahier peut être découpé en plusieurs PDF, d'où les listes.

**`DEFAULT_CHABIN_PDF_DIR`** — les PDF de transcription, nommés d'après l'URL d'origine
(donc identiques à `pdf_file`).

## `extract_contributions.py`

Découpe chaque PDF de transcription en contributions individuelles.

Dans ces PDF, chaque contribution est introduite par une ligne de titre en gris
(ex. « 1. Manuscrit … ») et terminée par une ligne de tirets bas. Le script saute les
pages d'introduction, rogne en-têtes et pieds de page, puis reconstitue les paires
titre / texte avec `pdfplumber`.

Pour chaque cahier, la sortie JSON contient les métadonnées de la commune, les
contributions extraites, le nombre attendu vs. trouvé (un écart est signalé sur la
sortie standard) et le lien vers les PDF bruts BnF correspondants.

```bash
python extract_contributions.py \
    --cahiers_json  <cahiers-chabin.json>   # produit par download_chabin_pdfs.py
    --pdf_dir       <PDF Chabin>            # téléchargés par download_chabin_pdfs.py
    --raw_pdf_dir   <PDF bruts BnF>         # pour associer chaque cahier à son scan
    --output        <extraction.json>
```

Tous les arguments ont une valeur par défaut définie en tête de fichier, relative à
`CAHIERS_DATA_DIR` (par défaut `data/` à la racine du dépôt).

### Sortie

**`--output`** — une liste JSON **alignée sur `cahiers-chabin.json`** : même longueur et
même ordre, avec `null` pour les communes sans PDF de transcription.

```json
[
  {
    "chabin_pdf_files": ["Cahier-de-doleances-de-La-Rochelle-1sur5-transcription.pdf"],  // dans --pdf_dir
    "num_contrib": 331,          // attendu, repris de cahiers-chabin.json
    "found_num_contrib": 329,    // réellement extrait
    "contributions": [
      {
        "title": "1. Manuscrit, 2 pages, 15 janvier 2019",  // ligne(s) de titre en gris
        "text": "Ligne 1\nLigne 2\n…"                       // texte, sauts de ligne du PDF
      }
    ],
    "city": {"insee": "17300", "commune": "La Rochelle", "habitants": 77205},
    "pdf_files": ["BnF_GDN_17_PDF/CC/…_17300_….pdf"]  // scans BnF, chemins relatifs
  }
]
```

Les contributions d'un cahier réparti sur plusieurs PDF sont concaténées dans l'ordre
des fichiers. Les blocs sans texte sont écartés.

Points de contrôle sur la sortie standard :

- `attendu N, trouvé M` : le découpage ne retrouve pas le compte annoncé — titre non
  détecté comme gris, séparateur absent ou contribution vide.
- `No matching pdf` / `Multiple match` : l'association au scan BnF a échoué ; `pdf_files`
  est alors vide ou ambigu.
- `Pas de pdfs: <commune>` : entrée mise à `null`.
- Bilan final : nombre total de contributions et de cahiers exportés.
