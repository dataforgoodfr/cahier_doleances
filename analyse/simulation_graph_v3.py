import json
import math
import os
from collections import Counter, defaultdict, deque
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
import plotly.offline
from fastapi import Body
from fastapi.responses import FileResponse, HTMLResponse, Response

import gradio as gr

RADIUS = 2 # profondeur du voisinage affiché autour du focus
CAP = 45 # plafond de nœuds dans le voisinage
APERCU_CAP = 260  # plafond de nœuds dans la vue d'ensemble
APERCU_ARBRES = 20  # plafond d'arbres dans la vue d'ensemble (v4 en compte 185)

BASE = Path(__file__).parent
DATA = BASE / "analysis_v4"
CORPUS = BASE / "analysis_v3" / "dataset.csv"   # corpus non livré en v4
STATIC = BASE / "static"


# --- 1. données ---
topics = json.loads((DATA / "taxonomy.json").read_text())["topics"]
docs = json.loads((DATA / "instances.json").read_text())["documents"]

by_id = {t["id"]: t for t in topics}
by_name = {t["name"]: t for t in topics}   # noms uniques en v4

# v4 ne livre pas le corpus ; on réutilise celui de v3, mêmes documents 0..1523.
# Il ne sert qu'à distinguer un verbatim littéral d'une reformulation.
content = ({str(r.id): r.content for r in pd.read_csv(CORPUS).itertuples()}
           if CORPUS.exists() else {})

occ = defaultdict(list)
for d in docs:
    for lab in d["labels"]:
        occ[lab["name"]].append((str(d["id"]), lab["rationale"], lab["extract"]))
own = {n: len(v) for n, v in occ.items()}
TOTAL_INST = sum(own.values())

# le parent est un UUID --> on le résout vers le nom
parent_nom = {t["name"]: (by_id[t["parent"]]["name"] if t["parent"] in by_id else None)
              for t in topics}


# --- 2. structure ---
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

_rec_memo = {}


def _rec(n):
    """Détections agrégées sur le sous-arbre."""
    if n not in _rec_memo:
        _rec_memo[n] = own.get(n, 0) + sum(_rec(c) for c in enfants[n])
    return _rec_memo[n]


def _sous_arbre(r):
    v, f = set(), deque([r])
    while f:
        x = f.popleft()
        if x in v:
            continue
        v.add(x)
        f.extend(enfants[x])
    return v


def _kids(n):
    return sorted(enfants[n], key=_rec, reverse=True)


# composantes connexes --> une racine par arbre, triées par détections
adj = defaultdict(set)
for n in propre:
    adj[n]
    if n in parent_de:
        adj[n].add(parent_de[n])
        adj[parent_de[n]].add(n)

_vus, _comps = set(), []
for _depart in adj:
    if _depart in _vus:
        continue
    _pile, _c = [_depart], []
    while _pile:
        _x = _pile.pop()
        if _x in _vus:
            continue
        _vus.add(_x)
        _c.append(_x)
        _pile.extend(adj[_x] - _vus)
    _comps.append(_c)

ROOTS = []
for _c in sorted(_comps, key=lambda c: -sum(own.get(n, 0) for n in c)):
    if sum(own.get(n, 0) for n in _c) == 0:
        continue
    ROOTS.append(next((n for n in _c if n not in parent_de), _c[0]))


# --- 3. profondeur et couleurs ---
PROFONDEUR = {}
for _r in (n for n in propre if n not in parent_de):
    PROFONDEUR[_r] = 0
    _f = deque([_r])
    while _f:
        _x = _f.popleft()
        for _e in enfants[_x]:
            PROFONDEUR[_e] = PROFONDEUR[_x] + 1
            _f.append(_e)
PROF_MAX = max(PROFONDEUR.values())


def _prof(n):
    return PROFONDEUR[n]


def _role_p(p):
    return "racine" if p == 0 else f"niveau {p}"


def _role(n):
    return _role_p(_prof(n))


# ordre validé : deux crans voisins restent distinguables, daltonisme inclus
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


# --- 4. strates ---
def _hauteur_arbre(r):
    d, f, mx = {r: 0}, deque([r]), 0
    while f:
        x = f.popleft()
        for c in enfants[x]:
            d[c] = d[x] + 1
            mx = max(mx, d[c])
            f.append(c)
    return mx


# strates de forêt : elles se définissent par la hauteur, comme notre critère
STRATES = [
    # clé, libellé, test sur la hauteur, part du cercle allouée
    ("A", "Canopée", lambda h: h >= 5, 0.62),          # hauteurs 6-7  -> 2 arbres
    ("B", "Sous-bois", lambda h: 3 <= h <= 4, 0.26),   # hauteurs 3-4  -> 5 arbres
    ("C", "Semis", lambda h: h <= 2, 0.12),            # hauteurs 1-2  -> 13 arbres
]
HAUTEUR = {r: _hauteur_arbre(r) for r in ROOTS}
STRATE_DE = {r: cle for r in ROOTS for cle, _, test, _ in STRATES if test(HAUTEUR[r])}
RACINES_STRATE = {cle: [r for r in ROOTS if STRATE_DE[r] == cle] for cle, _, _, _ in STRATES}
LIBELLE_STRATE = {cle: lib for cle, lib, _, _ in STRATES}

PROF_APERCU = {"A": 2, "B": 3, "C": 3}   # crans dépliés dans l'aperçu, par strate
APERCU = "— Vue d'ensemble —"            # sentinelle du 1er sélecteur


# --- 5. layout radial ---
def _squelette(prof_max, racines):
    """Les prof_max premiers crans sous la racine, plafonné à APERCU_CAP.
    Chaque nœud est relié à son plus proche ancêtre gardé."""
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
    """Part du cercle par arbre : budget fixe par strate, puis au prorata dedans.
    `poids` = feuilles affichées, pas le sous-arbre complet, sinon le secteur est
    calibré sur 3224 feuilles alors qu'on en dessine 40."""
    presents = [(cle, part) for cle, _, _, part in STRATES
                if any(STRATE_DE[r] == cle for r in racines)]
    somme_parts = sum(p for _, p in presents) or 1
    budgets = {}
    for cle, part in presents:
        grp = [r for r in racines if STRATE_DE[r] == cle]
        s = sum(max(1, poids.get(r, 1)) for r in grp)
        for r in grp:
            budgets[r] = (part / somme_parts) * max(1, poids.get(r, 1)) / s
    return budgets


def _layout_foret(keep, lien):
    """Un secteur angulaire par arbre, la profondeur donne le rayon."""
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

    budgets = _budgets([r for r in racines if r in STRATE_DE], largeur)

    prof = {}
    def marque(n, d):
        prof[n] = d
        for c in enf[n]:
            marque(c, d + 1)
    for r in racines:
        marque(r, 1)

    # rayon : assez d'écart pour que deux nœuds d'un même anneau ne se touchent pas
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

    # strate par strate : les arbres d'un même strate restent voisins à l'écran
    ordre_strates = {cle: i for i, (cle, _, _, _) in enumerate(STRATES)}
    racines = sorted(racines, key=lambda r: (ordre_strates.get(STRATE_DE.get(r), 9), -_rec(r)))
    cur = 0.0
    for r in racines:
        w = 2 * math.pi * budgets.get(r, 1 / len(racines))
        place(r, cur, cur + w)
        cur += w
    return pos


# --- 6. figures ---
def _trace_noeuds(noms, pos, seuil, taille, position_texte):
    return go.Scatter(
        x=[pos[n][0] for n in noms], y=[pos[n][1] for n in noms],
        mode="markers+text",
        text=[(n[:24] + "…" if len(n) > 24 else n) if _rec(n) >= seuil else "" for n in noms],
        textposition=position_texte(noms),
        textfont=dict(size=9, color="#334155"),
        customdata=noms,           # récupéré par plotly_click côté front
        hovertext=[f"{n}<br>{_role(n)} · {_rec(n)} détections" for n in noms],
        hoverinfo="text", showlegend=False,
        marker=dict(size=[taille(n) for n in noms],
                    color=[_couleur(n) for n in noms],
                    line=dict(width=1, color="#ffffff")),
    )


def _trace_aretes(paires, pos):
    ex, ey = [], []
    for a, b in paires:
        ex += [pos[a][0], pos[b][0], None]
        ey += [pos[a][1], pos[b][1], None]
    return go.Scatter(x=ex, y=ey, mode="lines", line=dict(width=1, color="#d1d5db"),
                      hoverinfo="none", showlegend=False)


def _legende(fig, noeuds):
    """Une entrée par cran présent, de la racine vers les feuilles."""
    feuilles_par_prof = {p: all(not enfants[n] for n in noeuds if _prof(n) == p)
                         for p in {_prof(n) for n in noeuds}}
    for p in sorted(feuilles_par_prof):
        etiq = " · feuilles" if p and feuilles_par_prof[p] else ""
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"{_role_p(p)}{etiq}",
                                 marker=dict(size=11, color=PROF_COULEUR[p % len(PROF_COULEUR)]),
                                 showlegend=True))


def _mise_en_page(fig, hauteur, egaliser):
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", xanchor="right", x=1, yanchor="bottom", y=0,
                    bgcolor="rgba(255,255,255,0.75)", bordercolor="#e5e7eb", borderwidth=1),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, **({"scaleanchor": "x", "scaleratio": 1} if egaliser else {})),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10), height=hauteur,
    )
    return fig


def _racines_apercu(strate):
    """Les arbres montrés dans l'aperçu : les plus gros d'abord. Au-delà d'une
    vingtaine, le layout radial devient un anneau illisible ; le reste de la
    strate reste accessible par le sélecteur."""
    return RACINES_STRATE[strate][:APERCU_ARBRES]


def figure_apercu(strate):
    keep, lien = _squelette(PROF_APERCU[strate], _racines_apercu(strate))
    pos = _layout_foret(keep, lien)
    noms = list(keep)
    seuil = sorted((_rec(n) for n in noms), reverse=True)[:22][-1] if len(noms) > 22 else 0
    paires = [(n, p) for n, p in lien.items() if p is not None and p in pos]
    fig = go.Figure([
        _trace_aretes(paires, pos),
        _trace_noeuds(noms, pos, seuil,
                      lambda n: 8 + min(round(_rec(n) ** 0.5) * 2, 30),
                      lambda ns: ["middle left" if pos[n][0] < 0 else "middle right" for n in ns]),
    ])
    _legende(fig, noms)
    return _mise_en_page(fig, hauteur=620, egaliser=True)


def _voisinage(focus):
    """BFS non orienté autour du focus, plafonné à CAP nœuds (les plus lourds
    d'abord à distance égale)."""
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


def figure_noeud(nom):
    """Focus au centre, voisinage à rayon 2 (Fruchterman-Reingold)."""
    dist = _voisinage(nom)
    G = nx.Graph()
    G.add_nodes_from(dist)
    for n in dist:
        if n in parent_de and parent_de[n] in dist:
            G.add_edge(n, parent_de[n])
    pos = nx.spring_layout(G, k=2.2 / (len(G) ** 0.5), seed=42,
                           pos={nom: (0, 0)}, fixed=[nom], iterations=200)
    noms = list(dist)
    seuil = sorted((_rec(n) for n in noms), reverse=True)[:18][-1] if len(noms) > 18 else 0
    fig = go.Figure([
        _trace_aretes(list(G.edges()), pos),
        _trace_noeuds(noms, pos, seuil,
                      lambda n: 12 + min(_rec(n), 24),
                      lambda ns: ["top center"] * len(ns)),
    ])
    fig.add_trace(go.Scatter(                       # anneau « vous êtes ici »
        x=[pos[nom][0]], y=[pos[nom][1]], mode="markers", name="sélection",
        marker=dict(size=20 + min(_rec(nom), 24), color="rgba(0,0,0,0)",
                    line=dict(width=3, color="#ef4444")), hoverinfo="skip"))
    _legende(fig, noms)
    return _mise_en_page(fig, hauteur=560, egaliser=False)


# --- 7. panneau et cascade ---
def _html_description(nom):
    t = by_name[nom]
    kids = enfants[nom]
    sous = f"{len(kids)} sous-thèmes" if kids else "aucun sous-thème (feuille)"
    return (
        f"<h3>{nom}</h3>"
        f"<p class='meta'><b>{_role(nom).capitalize()}</b> ({_prof(nom)} cran(s) sous la racine) "
        f"· <b>Parent</b> : {parent_de.get(nom, '— (racine)')} · {sous}</p>"
        f"<p class='meta'><b>Détections</b> : {_rec(nom)} au total · "
        f"{own.get(nom, 0)} sur ce topic</p>"
        f"<p>{t['description']}</p>"
    )


def _html_occurrences(nom):
    blocs = []
    for doc_id, rationale, extrait in occ.get(nom, [])[:6]:
        litteral = extrait[:40] in content.get(doc_id, "")
        cite = f"« {extrait.strip()} »" if litteral else f"<i>(reformulé)</i> {extrait.strip()}"
        blocs.append(f"<blockquote>{cite}<footer>— doc {doc_id} · {rationale}</footer></blockquote>")
    if not blocs:
        vide = ("Ce thème regroupe des sous-thèmes ; les occurrences sont sur les feuilles."
                if enfants[nom] else "Aucune occurrence sur ce topic.")
        blocs = [f"<p class='meta'><i>{vide}</i></p>"]
    return "<h4>Occurrences dans les textes</h4>" + "".join(blocs)


def _html_apercu(strate):
    rs = RACINES_STRATE[strate]
    total = sum(_rec(r) for r in ROOTS)
    dets = sum(_rec(r) for r in rs)
    hs = sorted({HAUTEUR[r] for r in rs})
    montres = _racines_apercu(strate)
    keep, _ = _squelette(PROF_APERCU[strate], montres)

    lignes = []
    for cle, lib, _test, _part in STRATES:
        g = RACINES_STRATE[cle]
        d = sum(_rec(r) for r in g)
        h = sorted({HAUTEUR[r] for r in g})
        courant = " class='ici'" if cle == strate else ""
        lignes.append(f"<tr{courant}><td>{cle} · {lib}</td><td>{h[0]}–{h[-1]}</td>"
                      f"<td>{len(g)}</td><td>{round(100 * d / total)} %</td></tr>")

    return (
        f"<h3>Strate {strate} · {LIBELLE_STRATE[strate]}</h3>"
        f"<p><b>{len(rs)} arbres · {dets} détections</b> "
        f"({round(100 * dets / total)} % du signal) · hauteur {hs[0]}–{hs[-1]}</p>"
        f"<p class='meta'>Aperçu : les <b>{len(montres)} arbres les plus gros</b> sur {len(rs)}, "
        f"jusqu'au cran {PROF_APERCU[strate]} sous la racine ({len(keep)} nœuds). "
        f"Les autres restent accessibles par le sélecteur.</p>"
        "<table><thead><tr><th>Strate</th><th>Hauteur</th><th>Arbres</th><th>Signal</th></tr>"
        "</thead><tbody>" + "".join(lignes) + "</tbody></table>"
        "<p class='meta'><b>Taille</b> = détections. <b>Couleur</b> = distance à la racine : "
        "toute racine porte la même couleur, quelle que soit la hauteur de son arbre.</p>"
    )


def _chemin(nom):
    """Ancêtres de `nom`, de la racine jusqu'à lui."""
    suite, cur = [], nom
    while cur is not None:
        suite.append(cur)
        cur = parent_de.get(cur)
    return list(reversed(suite))


def _opt(nom, avec_topics=False):
    """`value` = le nom brut attendu par l'API, `label` = ce qui s'affiche."""
    detail = f"{len(_sous_arbre(nom))} topics · " if avec_topics else ""
    return {"value": nom, "label": f"{nom} · {detail}{_rec(nom)} détections"}


def _options_racines(strate):
    return ([{"value": APERCU, "label": APERCU}]
            + [_opt(r, avec_topics=True) for r in RACINES_STRATE[strate]])


def _cascade(chemin, strate):
    """Toute la ligne de sélecteurs pour un chemin donné."""
    racines = _options_racines(strate)
    niveaux = []
    for i, node in enumerate(chemin):
        options = racines if i == 0 else [_opt(k) for k in _kids(chemin[i - 1])]
        niveaux.append({"label": "Racine · arbre" if i == 0 else _role(node).capitalize(),
                        "options": options, "value": node})
    if chemin:
        kids = _kids(chemin[-1])
        if kids:
            niveaux.append({"label": f"Descendre · {_role(kids[0])} ({len(kids)})",
                            "options": [_opt(k) for k in kids], "value": None})
    else:
        niveaux.append({"label": "Racine · arbre", "options": racines, "value": APERCU})
    return niveaux


# --- 8. serveur et routes ---
app = gr.Server()   # gr.Server hérite de FastAPI

_NO_STORE = {"Cache-Control": "no-store"}   # recharger reprend les static/ à jour


@app.get("/api/config")
def api_config():
    return {
        "apercu": APERCU,
        "strates": [{"value": cle, "label": f"{cle} · {LIBELLE_STRATE[cle]}"}
                    for cle in PROF_APERCU],
    }


@app.post("/api/apercu")
def api_apercu(strate: str = Body(..., embed=True)):
    if strate not in RACINES_STRATE:
        return {"erreur": f"strate inconnue : {strate}"}
    return {
        "figure": figure_apercu(strate).to_plotly_json(),
        "description": _html_apercu(strate),
        "occurrences": "",
        "strate": strate,
        "niveaux": _cascade([], strate),
    }


@app.post("/api/noeud")
def api_noeud(nom: str = Body(..., embed=True)):
    """Sert le clic comme le menu : on reçoit un nom, on recalcule tout le reste."""
    if nom not in propre:
        return {"erreur": f"topic inconnu : {nom}"}
    chemin = _chemin(nom)
    strate = STRATE_DE.get(chemin[0], "A")
    return {
        "figure": figure_noeud(nom).to_plotly_json(),
        "description": _html_description(nom),
        "occurrences": _html_occurrences(nom),
        "strate": strate,
        "niveaux": _cascade(chemin, strate),
    }


@app.get("/plotly.js")
def plotly_js():
    # servi depuis le paquet Python : pas de CDN, marche hors-ligne
    return Response(plotly.offline.get_plotlyjs(), media_type="text/javascript")


@app.get("/")
def index():
    return HTMLResponse((STATIC / "index.html").read_text(encoding="utf-8"), headers=_NO_STORE)


@app.get("/app.js")
def app_js():
    return FileResponse(STATIC / "app.js", media_type="text/javascript", headers=_NO_STORE)


@app.get("/style.css")
def style_css():
    return FileResponse(STATIC / "style.css", media_type="text/css", headers=_NO_STORE)


if __name__ == "__main__":
    app.launch(server_port=int(os.getenv("PORT", "7861")),
               allowed_paths=[str(STATIC)])
