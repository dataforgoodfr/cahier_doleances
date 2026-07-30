"""Simulation Gradio — vue graphe des topics de JB (POC, lit les fichiers bruts).

Données : livraison v3 (analysis_v3), hiérarchie à 8 niveaux (level 0→7).
- parent est un UUID (v3) → résolu vers le nom (les noms sont uniques) ;
- filtre de vue : on écarte isolés + cycles (quasi nuls en v3) ;
- les 20 arbres sont rangés en PALIERS par hauteur (A : 6-7 · B : 3-4 · C : 1-2),
  car ils n'ont rien de comparable : 2 arbres portent 95 % du signal, 13 en portent 1 % ;
- un palier = une vue : on entre par une racine (le cluster le plus généraliste)
  et on descend vers les feuilles. Layout RADIAL de forêt, secteur alloué par
  PALIER sinon les 2 géants écrasent tout ;
- navigation = CASCADE DYNAMIQUE de sélecteurs : un dropdown par cran du chemin,
  ils apparaissent à mesure qu'on descend (les codes du 4-niveaux, scalés à 8) ;
- couleur = PROFONDEUR depuis la racine de son arbre, PAS le `level` de JB : ses
  20 racines sont aux levels {1,2,3,4,6,7}, donc deux points d'entrée équivalents
  recevaient deux couleurs. Toute racine = profondeur 0 = même couleur ;
- taille = détections agrégées.

Lancer :  uv run python analyse/simulation_graph_v2.py
"""
import json
import math
from collections import Counter, defaultdict, deque
from functools import partial
from pathlib import Path

import gradio as gr
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

RADIUS = 2   # profondeur du voisinage affiché autour du focus
CAP = 45     # plafond de nœuds dans le voisinage
APERCU_CAP = 260  # plafond de nœuds dans la vue d'ensemble

DATA = Path(__file__).parent / "analysis_v3"

# ---- chargement (v3) ----
topics = json.loads((DATA / "structure/taxonomy_32.json").read_text())["topics"]
docs = json.loads((DATA / "label/instances.json").read_text())["documents"]
df = pd.read_csv(DATA / "dataset.csv")

by_id = {t["id"]: t for t in topics}
by_name = {t["name"]: t for t in topics}          # noms uniques en v3 (0 doublon)
content = {str(r.id): r.content for r in df.itertuples()}

occ = defaultdict(list)
for d in docs:
    for lab in d["labels"]:
        occ[lab["name"]].append((str(d["id"]), lab["rationale"], lab["extract"]))
own = {n: len(v) for n, v in occ.items()}
TOTAL_INST = sum(own.values())

# parent est un UUID en v3 → on le résout vers le NOM du parent
parent_nom = {t["name"]: (by_id[t["parent"]]["name"] if t["parent"] in by_id else None)
              for t in topics}

# ---- filtre de vue : isolés + cycles ----
est_parent = {p for p in parent_nom.values() if p}
isoles = {n for n in by_name if not parent_nom[n] and n not in est_parent}


def _cyclique(nom, vus=None):
    vus = vus or set()
    if nom in vus:
        return True
    vus.add(nom)
    p = parent_nom.get(nom)
    return _cyclique(p, vus) if p and p in by_name else False


cycliques = {n for n in by_name if _cyclique(n)}
propre = set(by_name) - isoles - cycliques

parent_de = {n: parent_nom[n] for n in propre if parent_nom[n] in propre}
enfants = defaultdict(list)
for n, p in parent_de.items():
    enfants[p].append(n)


# ---- détections agrégées (mémoïsé : arbre acyclique) ----
_rec_memo = {}


def _rec(n):
    if n not in _rec_memo:
        _rec_memo[n] = own.get(n, 0) + sum(_rec(c) for c in enfants[n])
    return _rec_memo[n]


def _niveau(n):
    return by_name[n]["level"]


# ---- composantes (arbres) ----
adj = defaultdict(set)
for n in propre:
    adj[n]
    if n in parent_de:
        adj[n].add(parent_de[n])
        adj[parent_de[n]].add(n)

vus, comps = set(), []
for depart in adj:
    if depart in vus:
        continue
    pile, c = [depart], []
    while pile:
        x = pile.pop()
        if x in vus:
            continue
        vus.add(x)
        c.append(x)
        pile.extend(adj[x] - vus)
    comps.append(c)

ROOTS = []
for c in sorted(comps, key=lambda c: -sum(own.get(n, 0) for n in c)):
    if sum(own.get(n, 0) for n in c) == 0:
        continue
    ROOTS.append(next((n for n in c if n not in parent_de), c[0]))

# ---- PROFONDEUR depuis la racine de son arbre (0 = racine) ----
# C'est ça qui donne la couleur, PAS le champ `level` de JB. Raison : les 20
# racines sont déclarées aux levels {1,2,3,4,6,7} — deux points d'entrée
# équivalents (sciences humaines et sociales / sciences sociales) recevaient
# donc deux couleurs différentes. Avec la profondeur, toute racine vaut 0.
# Bonus : la couleur d'un topic ne dépend plus de ce qui est à l'écran.
PROFONDEUR = {}
for _r in (n for n in propre if n not in parent_de):
    PROFONDEUR[_r] = 0
    _f = deque([_r])
    while _f:
        _x = _f.popleft()
        for _c in enfants[_x]:
            PROFONDEUR[_c] = PROFONDEUR[_x] + 1
            _f.append(_c)
PROF_MAX = max(PROFONDEUR.values())


def _prof(n):
    return PROFONDEUR[n]


def _role_p(p):
    """Nom du cran : on entre par la racine (0) et on descend vers les feuilles."""
    return "racine" if p == 0 else f"niveau {p}"


def _role(n):
    return _role_p(_prof(n))


# Ordre catégoriel validé (ΔE adjacents : 9.1 daltonisme / 19.6 vision normale).
# Il compte : une arête relie toujours deux crans VOISINS, donc ce sont les
# paires adjacentes qui doivent se distinguer.
PROF_COULEUR = ["#2a78d6",  # 0 bleu — racine
                "#eb6834",  # 1 orange
                "#1baf7a",  # 2 aqua
                "#eda100",  # 3 jaune
                "#e87ba4",  # 4 magenta
                "#008300",  # 5 vert
                "#4a3aa7",  # 6 violet
                "#e34948"]  # 7 rouge


def _couleur(n):
    return PROF_COULEUR[_prof(n) % len(PROF_COULEUR)]


def _legende(fig, noeuds):
    """Une entrée par CRAN présent, de la racine vers les feuilles."""
    feuilles_par_prof = {p: all(not enfants[n] for n in noeuds if _prof(n) == p)
                         for p in {_prof(n) for n in noeuds}}
    for p in sorted(feuilles_par_prof):
        etiq = " · feuilles" if p and feuilles_par_prof[p] else ""
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"{_role_p(p)}{etiq}",
                                 marker=dict(size=11, color=PROF_COULEUR[p % len(PROF_COULEUR)]),
                                 showlegend=True))


# ---- paliers : regrouper les 20 arbres par HAUTEUR ----
# On a vérifié que hauteur d'un arbre == niveau de sa racine (20/20).
# Sans ça, le secteur angulaire est alloué au prorata des feuilles : les 2 géants
# (95 % des nœuds) écrasent les 18 autres. Le palier rééquilibre l'espace.
def _hauteur_arbre(r):
    d, f, mx = {r: 0}, deque([r]), 0
    while f:
        x = f.popleft()
        for c in enfants[x]:
            d[c] = d[x] + 1
            mx = max(mx, d[c])
            f.append(c)
    return mx


PALIERS = [
    ("A", "Grands domaines", lambda h: h >= 5, 0.62),        # hauteurs 6-7  → 2 arbres
    ("B", "Domaines intermédiaires", lambda h: 3 <= h <= 4, 0.26),  # hauteurs 3-4 → 5 arbres
    ("C", "Fragments", lambda h: h <= 2, 0.12),              # hauteurs 1-2 → 13 arbres
]
HAUTEUR = {r: _hauteur_arbre(r) for r in ROOTS}
PALIER_DE = {r: cle for r in ROOTS for cle, _, test, _ in PALIERS if test(HAUTEUR[r])}
RACINES_PALIER = {cle: [r for r in ROOTS if PALIER_DE[r] == cle] for cle, _, _, _ in PALIERS}
LIBELLE_PALIER = {cle: lib for cle, lib, _, _ in PALIERS}


def _kids(n):
    return sorted(enfants[n], key=_rec, reverse=True)


# ---- voisinage (focus + rayon 2) ----
def _voisinage(focus):
    dist = {focus: 0}
    file = deque([focus])
    while file:
        n = file.popleft()
        if dist[n] >= RADIUS:
            continue
        voisins = ([parent_de[n]] if n in parent_de else []) + enfants[n]
        for v in sorted(voisins, key=_rec, reverse=True):
            if v not in dist:
                dist[v] = dist[n] + 1
                file.append(v)
    if len(dist) <= CAP:
        return dist
    garde = sorted(dist, key=lambda n: (dist[n], -_rec(n)))[:CAP]
    return {n: dist[n] for n in garde}


def _figure(focus):
    dist = _voisinage(focus)
    G = nx.Graph()
    G.add_nodes_from(dist)
    for n in dist:
        if n in parent_de and parent_de[n] in dist:
            G.add_edge(n, parent_de[n])
    pos = nx.spring_layout(G, k=2.2 / (len(G) ** 0.5), seed=42,
                           pos={focus: (0, 0)}, fixed=[focus], iterations=200)

    ex, ey = [], []
    for a, b in G.edges():
        ex += [pos[a][0], pos[b][0], None]
        ey += [pos[a][1], pos[b][1], None]
    edges = go.Scatter(x=ex, y=ey, mode="lines",
                       line=dict(width=1, color="#d1d5db"), hoverinfo="none", showlegend=False)

    ordre = list(dist)
    seuil = sorted((_rec(n) for n in ordre), reverse=True)[:18][-1] if len(ordre) > 18 else 0

    def _label(n):
        if not (dist[n] <= 1 or _rec(n) >= seuil or n == focus):
            return ""
        return n[:24] + "…" if len(n) > 24 else n

    nodes = go.Scatter(
        x=[pos[n][0] for n in ordre], y=[pos[n][1] for n in ordre],
        mode="markers+text", text=[_label(n) for n in ordre],
        textposition="top center", textfont=dict(size=10, color="#334155"),
        hovertext=[f"{n}<br>{_role(n)} · {_rec(n)} détections" for n in ordre],
        hoverinfo="text", showlegend=False,
        marker=dict(size=[12 + min(_rec(n), 24) for n in ordre],
                    color=[_couleur(n) for n in ordre], line=dict(width=1.5, color="#ffffff")),
    )
    fig = go.Figure([edges, nodes])
    fig.add_trace(go.Scatter(
        x=[pos[focus][0]], y=[pos[focus][1]], mode="markers", name="sélection",
        marker=dict(size=20 + min(_rec(focus), 24), color="rgba(0,0,0,0)",
                    line=dict(width=3, color="#ef4444")), hoverinfo="skip"))
    _legende(fig, ordre)
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", xanchor="right", x=1, yanchor="bottom", y=0,
                    bgcolor="rgba(255,255,255,0.75)", bordercolor="#e5e7eb", borderwidth=1),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10), height=560,
    )
    return fig


# ---- vue d'ensemble : squelette des sommets d'arbres ----
def _sous_arbre(r):
    v, f = set(), deque([r])
    while f:
        x = f.popleft()
        if x in v:
            continue
        v.add(x)
        f.extend(enfants[x])
    return v


def _squelette(prof_max, racines):
    """Les prof_max premiers crans sous la racine, plafonné à APERCU_CAP (les
    plus lourds d'abord). Chaque nœud est relié à son plus proche ancêtre gardé."""
    portee = set().union(*(_sous_arbre(r) for r in racines)) if racines else set()
    keep = {n for n in portee if _prof(n) <= prof_max}
    if len(keep) > APERCU_CAP:
        keep = set(sorted(keep, key=_rec, reverse=True)[:APERCU_CAP]) | set(racines)
    lien = {}
    for n in keep:
        p = parent_de.get(n)
        while p is not None and p not in keep:
            p = parent_de.get(p)
        lien[n] = p
    return keep, lien


def _budgets(racines, poids):
    """Fraction du cercle par arbre : d'abord un budget FIXE par palier, puis au
    prorata à l'intérieur du palier. Sans ça les 2 géants (95 % des nœuds)
    écrasent les 18 autres jusqu'à l'illisibilité.
    `poids` = nb de feuilles RÉELLEMENT AFFICHÉES (pas du sous-arbre complet) :
    sinon le secteur est calibré sur 3224 feuilles alors qu'on en dessine 40,
    et les nœuds s'empilent."""
    presents = [(cle, part) for cle, _, _, part in PALIERS
                if any(PALIER_DE[r] == cle for r in racines)]
    somme_parts = sum(p for _, p in presents) or 1
    budgets = {}
    for cle, part in presents:
        grp = [r for r in racines if PALIER_DE[r] == cle]
        s = sum(max(1, poids.get(r, 1)) for r in grp)
        for r in grp:
            budgets[r] = (part / somme_parts) * max(1, poids.get(r, 1)) / s
    return budgets


def _layout_foret(keep, lien, reserve=0.0):
    """Layout radial de forêt : un secteur angulaire par arbre, la profondeur
    donne le rayon → pas de chevauchement. La largeur du secteur vient du
    PALIER (budget fixe), pas du nombre brut de feuilles.
    `reserve` = fraction du cercle laissée libre (pour le bloc Fragments)."""
    enf = defaultdict(list)
    for n, p in lien.items():
        if p is not None:
            enf[p].append(n)
    for p in enf:
        enf[p].sort(key=_rec, reverse=True)
    racines = sorted((n for n in keep if lien[n] is None), key=_rec, reverse=True)

    largeur = {}
    def compte(n):
        if n not in largeur:
            largeur[n] = 1 if not enf[n] else sum(compte(c) for c in enf[n])
        return largeur[n]
    for r in racines:
        compte(r)

    # budget calculé sur les feuilles AFFICHÉES (largeur), pas le sous-arbre complet
    budgets = _budgets([r for r in racines if r in PALIER_DE], largeur)

    prof = {}
    def marque(n, d):
        prof[n] = d
        for c in enf[n]:
            marque(c, d + 1)
    for r in racines:
        marque(r, 1)

    # rayon : assez d'écart pour que deux nœuds voisins d'un même anneau ne se
    # touchent pas (0.9 ≈ diamètre max d'un marqueur en unités de données)
    R0 = max(1.4, max((c * 0.9) / (2 * math.pi * d) for d, c in Counter(prof.values()).items()))
    pos = {}
    def place(n, a0, a1):
        a = (a0 + a1) / 2
        pos[n] = (R0 * prof[n] * math.cos(a), R0 * prof[n] * math.sin(a))
        cur = a0
        for c in enf[n]:
            w = (a1 - a0) * largeur[c] / largeur[n]
            place(c, cur, cur + w)
            cur += w
    # on parcourt palier par palier : les arbres d'un même palier restent voisins
    ordre_paliers = {cle: i for i, (cle, _, _, _) in enumerate(PALIERS)}
    racines = sorted(racines, key=lambda r: (ordre_paliers.get(PALIER_DE.get(r), 9), -_rec(r)))
    dispo = 2 * math.pi * (1 - reserve)
    secteurs, cur = {}, 0.0
    for r in racines:
        w = dispo * budgets.get(r, 1 / len(racines))
        place(r, cur, cur + w)
        secteurs[r] = (cur, cur + w)
        cur += w
    return pos, enf, secteurs


def _figure_apercu(prof_max, palier):
    """Vue d'un palier : ses arbres, des racines jusqu'au cran prof_max."""
    racines = RACINES_PALIER[palier]
    keep, lien = _squelette(prof_max, racines)
    pos, enf, secteurs = _layout_foret(keep, lien)

    ex, ey = [], []
    for n, p in lien.items():
        if p is not None and p in pos:
            ex += [pos[n][0], pos[p][0], None]
            ey += [pos[n][1], pos[p][1], None]
    edges = go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=1, color="#d1d5db"),
                       hoverinfo="none", showlegend=False)

    ordre = list(keep)
    seuil = sorted((_rec(n) for n in ordre), reverse=True)[:22][-1] if len(ordre) > 22 else 0
    nodes = go.Scatter(
        x=[pos[n][0] for n in ordre], y=[pos[n][1] for n in ordre],
        mode="markers+text",
        text=[(n[:24] + "…" if len(n) > 24 else n) if _rec(n) >= seuil else "" for n in ordre],
        textposition=["middle left" if pos[n][0] < 0 else "middle right" for n in ordre],
        textfont=dict(size=9, color="#334155"),
        hovertext=[f"{n}<br>{_role(n)} · {_rec(n)} détections" for n in ordre],
        hoverinfo="text", showlegend=False,
        marker=dict(size=[8 + min(round(_rec(n) ** 0.5) * 2, 30) for n in ordre],
                    color=[_couleur(n) for n in ordre], line=dict(width=1, color="#ffffff")),
    )
    fig = go.Figure([edges, nodes])
    _legende(fig, ordre)
    titre = f"Palier {palier} · {LIBELLE_PALIER[palier]}"
    fig.add_annotation(x=0, y=1, xref="paper", yref="paper", text=titre,
                       showarrow=False, xanchor="left", yanchor="bottom",
                       font=dict(size=11, color="#52514e"))
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", xanchor="right", x=1, yanchor="bottom", y=0,
                    bgcolor="rgba(255,255,255,0.75)", bordercolor="#e5e7eb", borderwidth=1),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=30, b=10), height=620,
    )
    return fig


def _description(nom):
    t = by_name[nom]
    sous = f"{len(enfants[nom])} sous-thèmes" if enfants[nom] else "aucun sous-thème (feuille)"
    return (
        f"### {nom}\n"
        f"**{_role(nom).capitalize()}** ({_prof(nom)} cran(s) sous la racine) · "
        f"**Parent** : {t['parent'] and by_id.get(t['parent'], {}).get('name') or '— (racine)'} · {sous}\n\n"
        f"**Détections** : {_rec(nom)} au total · {own.get(nom, 0)} sur ce topic\n\n"
        f"{t['description']}"
    )


def _occurrences(nom):
    lignes = []
    for doc_id, rationale, extract in occ.get(nom, [])[:8]:
        literal = extract[:40] in content.get(doc_id, "")
        cite = f"« {extract.strip()} »" if literal else f"*(reformulé)* {extract.strip()}"
        lignes.append(f"> {cite}\n>\n> — doc {doc_id} · {rationale}")
    corps = "\n\n".join(lignes) if lignes else (
        "*Ce thème regroupe des sous-thèmes ; les occurrences sont sur les topics feuilles.*"
        if enfants[nom] else "*Aucune occurrence sur ce topic.*"
    )
    return f"#### Occurrences dans les textes\n{corps}"


# ---- interface ----
# le sélecteur d'entrée = le PALIER (groupe d'arbres). Un palier = une vue.
# prof_max : jusqu'à quel cran sous la racine on déplie l'aperçu.
VUE_CHOIX = {}
for _cle, _lib, _test, _ in PALIERS:
    _rs = RACINES_PALIER[_cle]
    VUE_CHOIX[f"Palier {_cle} · {_lib} ({len(_rs)} arbres)"] = (2 if _cle == "A" else 3, _cle)
VUE_DEFAUT = next(iter(VUE_CHOIX))


def _apercu_md(vue):
    prof_max, palier = VUE_CHOIX[vue]
    dets_tot = sum(_rec(r) for r in ROOTS)
    rs = RACINES_PALIER[palier]
    keep, _ = _squelette(prof_max, rs)
    dets = sum(_rec(r) for r in rs)
    hs = sorted({HAUTEUR[r] for r in rs})
    lignes = []
    for cle, lib, _, _ in PALIERS:
        g = RACINES_PALIER[cle]
        d = sum(_rec(r) for r in g)
        h = sorted({HAUTEUR[r] for r in g})
        lignes.append(f"| {cle} · {lib} | {h[0]}–{h[-1]} | {len(g)} | "
                      f"{round(100 * d / dets_tot)} % | {'**←**' if cle == palier else ''} |")
    return (
        f"### Palier {palier} · {LIBELLE_PALIER[palier]}\n"
        f"**{len(rs)} arbres · {dets} détections** "
        f"({round(100 * dets / dets_tot)} % du signal) · hauteur {hs[0]}–{hs[-1]}\n\n"
        f"Aperçu : les **{prof_max + 1} premiers crans** sous la racine "
        f"({len(keep)} nœuds) ; le reste apparaît en descendant.\n\n"
        f"| Palier | Hauteur | Arbres | Signal | |\n|---|---|---|---|---|\n"
        + "\n".join(lignes) + "\n\n"
        "L'espace du cercle est réparti **par palier**, sinon les 2 géants "
        "(95 % des nœuds) écrasent les 18 autres.\n\n"
        "**Taille** = détections. **Couleur** = distance à la racine : toute racine "
        "porte la même couleur, quelle que soit la hauteur de son arbre.\n\n"
        "Choisis une racine, puis descends — un sélecteur apparaît à chaque cran."
    )


# Sélecteurs FIXES (comme la version de référence) plutôt que dynamiques : ils
# sont créés une fois, dans une seule Row, et on les montre/masque via
# gr.update(). PROF_MAX crans suffisent pour la branche la plus profonde.
NB_CRANS = PROF_MAX


def _vide(depuis):
    """Vide et masque les sélecteurs de cran de `depuis` à la fin."""
    return [gr.update(choices=[], value=None, visible=False)
            for _ in range(depuis, NB_CRANS)]


def _ouvre(focus, i):
    """Sélecteur de cran i = les enfants de `focus` ; le reste est vidé.
    Renvoie exactement NB_CRANS - i mises à jour."""
    if i >= NB_CRANS:
        return []
    kids = _kids(focus)
    if not kids:
        return _vide(i)
    tete = gr.update(choices=kids, value=None, visible=True,
                     label=f"Descendre · {_role(kids[0])} ({len(kids)})")
    return [tete] + _vide(i + 1)


# sentinelle du 1er sélecteur : revenir à la structure d'ensemble du palier
# (reprend le code de navigation de la version de référence)
APERCU = "— Vue d'ensemble —"


def _racines_du_palier(vue):
    """Racines proposées à l'entrée : celles du palier, + le retour à l'aperçu."""
    _, palier = VUE_CHOIX[vue]
    return [APERCU] + RACINES_PALIER[palier]


def _apercu(vue):
    """Retour à la structure d'ensemble du palier : aucun nœud en focus."""
    prof_max, palier = VUE_CHOIX[vue]
    return (_figure_apercu(prof_max, palier), _apercu_md(vue), "", None, *_vide(0))


def _aller(node, i):
    """Focus sur `node` ; le sélecteur de cran i propose ses enfants."""
    return (_figure(node), _description(node), _occurrences(node), node, *_ouvre(node, i))


def on_palier(vue):
    """Changer de palier : la liste des racines change, la navigation repart à zéro."""
    return (gr.update(choices=_racines_du_palier(vue), value=APERCU), *_apercu(vue))


def on_racine(root, vue):
    if not root or root == APERCU:
        return _apercu(vue)
    return _aller(root, 0)


def on_cran(node, i):
    """Descente depuis le cran i : focus sur `node`, on ouvre le cran i+1.
    Les crans 0..i gardent leur valeur (gr.update() vide = inchangé)."""
    if not node:                       # reset programmatique : on ne touche à rien
        return (gr.update(),) * (4 + NB_CRANS)
    fig, desc, occ, focus, *suite = _aller(node, i + 1)
    return (fig, desc, occ, focus, *([gr.update()] * (i + 1)), *suite)


with gr.Blocks(title="Doléances — thèmes") as demo:
    gr.Markdown("### Cahiers de doléances — exploration des thèmes (POC · données v3, 8 niveaux)")
    focus_state = gr.State()

    # UNE seule ligne de sélecteurs FIXES, comme la version de référence :
    # Palier (≈ Profondeur) | Racine · arbre | les crans successifs (masqués au départ)
    with gr.Row():
        palier_dd = gr.Dropdown(list(VUE_CHOIX), value=VUE_DEFAUT, label="Palier d'entrée",
                                filterable=False, scale=1)
        racine_dd = gr.Dropdown(_racines_du_palier(VUE_DEFAUT), value=APERCU,
                                label="Racine · arbre", filterable=True, scale=1)
        crans_dd = [gr.Dropdown(label=f"Cran {i + 1}", filterable=True, visible=False, scale=1)
                    for i in range(NB_CRANS)]

    with gr.Row():
        with gr.Column(scale=2):
            plot = gr.Plot()
        with gr.Column(scale=1):
            description = gr.Markdown()
            occurrences = gr.Markdown()

    vue_sorties = [plot, description, occurrences, focus_state, *crans_dd]
    palier_dd.change(on_palier, palier_dd, [racine_dd, *vue_sorties])
    racine_dd.change(on_racine, [racine_dd, palier_dd], vue_sorties)
    # descendre depuis le cran i ouvre le cran i+1 ; les crans 0..i restent tels quels
    for _i, _dd in enumerate(crans_dd):
        _dd.change(partial(on_cran, i=_i), _dd, vue_sorties)
    demo.load(on_palier, palier_dd, [racine_dd, *vue_sorties])


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
