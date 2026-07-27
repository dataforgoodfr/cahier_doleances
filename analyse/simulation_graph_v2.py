"""Simulation Gradio — vue graphe des topics de JB (POC, lit les fichiers bruts).

Données : livraison v3 (analysis_v3), hiérarchie à 8 niveaux (level 0→7).
- parent est un UUID (v3) → résolu vers le nom (les noms sont uniques) ;
- filtre de vue : on écarte isolés + cycles (quasi nuls en v3) ;
- vue d'ensemble = squelette des sommets d'arbres, layout RADIAL de forêt
  (un secteur angulaire par arbre, profondeur = rayon) : pas de chevauchement ;
- navigation = CASCADE DYNAMIQUE de sélecteurs : un dropdown par niveau du chemin,
  ils apparaissent à mesure qu'on descend (les codes du 4-niveaux, scalés à 8) ;
- couleur = niveau dans l'arbre (un ton distinct par niveau), taille = détections agrégées.

Lancer :  uv run python analyse/simulation_graph_v2.py
"""
import json
import math
from collections import Counter, defaultdict, deque
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

# ---- couleur DISTINCTE par NIVEAU dans l'arbre ----
# un ton franc par niveau (comme la version de référence à 4 couleurs), pas un
# dégradé et surtout PAS une couleur par thème : la couleur dit la profondeur
NIVEAU_MAX = max(_niveau(n) for n in propre)
NIVEAU_COULEUR = ["#059669",  # 0 vert (feuille)
                  "#d97706",  # 1 orange
                  "#2563eb",  # 2 bleu
                  "#7c3aed",  # 3 violet
                  "#db2777",  # 4 rose
                  "#0891b2",  # 5 cyan
                  "#65a30d",  # 6 olive
                  "#4338ca"]  # 7 indigo (racine)


def _couleur(n):
    return NIVEAU_COULEUR[_niveau(n) % len(NIVEAU_COULEUR)]


def _legende(fig, noeuds):
    """Une entrée de légende par NIVEAU présent (ton distinct par niveau)."""
    for lvl in sorted({_niveau(n) for n in noeuds}):
        etiq = " · feuille" if lvl == 0 else " · racine" if lvl == NIVEAU_MAX else ""
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", name=f"niveau {lvl}{etiq}",
                                 marker=dict(size=11, color=NIVEAU_COULEUR[lvl % len(NIVEAU_COULEUR)]),
                                 showlegend=True))


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
        hovertext=[f"{n}<br>niveau {_niveau(n)} · {_rec(n)} détections" for n in ordre],
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
def _squelette(niveau_min):
    """Nœuds de niveau ≥ niveau_min + racines d'arbres, plafonné à APERCU_CAP
    (les plus lourds d'abord). Chaque nœud est relié à son plus proche ancêtre gardé."""
    keep = {n for n in propre if _niveau(n) >= niveau_min or n in ROOTS}
    if len(keep) > APERCU_CAP:
        keep = set(sorted(keep, key=_rec, reverse=True)[:APERCU_CAP]) | set(ROOTS)
    lien = {}
    for n in keep:
        p = parent_de.get(n)
        while p is not None and p not in keep:
            p = parent_de.get(p)
        lien[n] = p
    return keep, lien


def _layout_foret(keep, lien):
    """Layout radial de forêt : un secteur angulaire par arbre (largeur ∝ nb de
    feuilles), la profondeur donne le rayon → pas de chevauchement entre arbres."""
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
    total = sum(compte(r) for r in racines) or 1

    prof = {}
    def marque(n, d):
        prof[n] = d
        for c in enf[n]:
            marque(c, d + 1)
    for r in racines:
        marque(r, 1)

    R0 = max(1.0, max((c * 0.55) / (2 * math.pi * d) for d, c in Counter(prof.values()).items()))
    pos = {}
    def place(n, a0, a1):
        a = (a0 + a1) / 2
        pos[n] = (R0 * prof[n] * math.cos(a), R0 * prof[n] * math.sin(a))
        cur = a0
        for c in enf[n]:
            w = (a1 - a0) * largeur[c] / largeur[n]
            place(c, cur, cur + w)
            cur += w
    cur = 0.0
    for r in racines:
        w = 2 * math.pi * largeur[r] / total
        place(r, cur, cur + w)
        cur += w
    return pos, enf


def _figure_apercu(niveau_min):
    keep, lien = _squelette(niveau_min)
    pos, enf = _layout_foret(keep, lien)

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
        hovertext=[f"{n}<br>niveau {_niveau(n)} · {_rec(n)} détections" for n in ordre],
        hoverinfo="text", showlegend=False,
        marker=dict(size=[8 + min(round(_rec(n) ** 0.5) * 2, 30) for n in ordre],
                    color=[_couleur(n) for n in ordre], line=dict(width=1, color="#ffffff")),
    )
    fig = go.Figure([edges, nodes])
    _legende(fig, ordre)
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="v", xanchor="right", x=1, yanchor="bottom", y=0,
                    bgcolor="rgba(255,255,255,0.75)", bordercolor="#e5e7eb", borderwidth=1),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, scaleanchor="x", scaleratio=1),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10), height=620,
    )
    return fig


def _description(nom):
    t = by_name[nom]
    sous = f"{len(enfants[nom])} sous-thèmes" if enfants[nom] else "aucun sous-thème (feuille)"
    return (
        f"### {nom}\n"
        f"**Niveau** : {_niveau(nom)} / {NIVEAU_MAX} · **Parent** : {t['parent'] and by_id.get(t['parent'], {}).get('name') or '— (racine)'} · {sous}\n\n"
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
# profondeur d'aperçu : à partir de quel niveau on montre le squelette
VUE_CHOIX = {"Sommets (niveau ≥ 4)": 4, "Intermédiaire (niveau ≥ 3)": 3, "Large (niveau ≥ 2)": 2}
VUE_DEFAUT = "Intermédiaire (niveau ≥ 3)"


def _apercu_md(vue):
    nmin = VUE_CHOIX[vue]
    keep, _ = _squelette(nmin)
    dets = sum(_rec(r) for r in ROOTS)
    return (
        f"### Vue d'ensemble\n"
        f"**{len(ROOTS)} arbres · {dets} détections** ({round(100 * dets / TOTAL_INST)} % du total) · "
        f"{len(docs)} documents analysés sur {len(df)}\n\n"
        f"Hiérarchie à **{NIVEAU_MAX + 1} niveaux** (0 feuille → {NIVEAU_MAX} racine). "
        f"Le graphe montre le **squelette** ({len(keep)} nœuds de niveau ≥ {nmin}) ; "
        f"les niveaux plus fins apparaissent au zoom. **Taille** = détections, **couleur** = niveau.\n\n"
        f"Choisis une racine, puis descends niveau par niveau — un sélecteur apparaît à chaque cran."
    )


def _lbl(node, i):
    """Libellé du sélecteur du niveau i du chemin (racine = 0)."""
    return "Racine · arbre" if i == 0 else f"Niveau {_niveau(node)}"


def update_view(path, vue):
    """Bascule l'affichage : vue d'ensemble si le chemin est vide, sinon le nœud courant."""
    if not path:
        return _figure_apercu(VUE_CHOIX[vue]), _apercu_md(vue), ""
    node = path[-1]
    return _figure(node), _description(node), _occurrences(node)


with gr.Blocks(title="Doléances — thèmes") as demo:
    gr.Markdown("### Cahiers de doléances — exploration des thèmes (POC · données v3, 8 niveaux)")
    # chemin racine → nœud courant ; sa longueur = nb de sélecteurs affichés
    path_state = gr.State([])

    vue_dd = gr.Dropdown(list(VUE_CHOIX), value=VUE_DEFAUT, label="Profondeur d'aperçu",
                         filterable=False)

    @gr.render(inputs=path_state)
    def cascade(path):
        # un sélecteur par niveau du chemin (+ un pour descendre encore) ;
        # changer un sélecteur ré-enracine la descente à partir de ce niveau
        with gr.Row():
            if not path:
                dd = gr.Dropdown(ROOTS, value=None, label="Racine · arbre", filterable=True)
                dd.change(lambda v: [v] if v else [], dd, path_state)
            else:
                for i, node in enumerate(path):
                    options = ROOTS if i == 0 else _kids(path[i - 1])
                    dd = gr.Dropdown(options, value=node, label=_lbl(node, i), filterable=True)
                    dd.change(lambda v, p, i=i: (p[:i] + [v]) if v else p[:i],
                              [dd, path_state], path_state)
                kids = _kids(path[-1])
                if kids:
                    ddn = gr.Dropdown(kids, value=None, filterable=True,
                                      label=f"Descendre · niveau {_niveau(kids[0])} ({len(kids)})")
                    ddn.change(lambda v, p: (p + [v]) if v else p, [ddn, path_state], path_state)

    with gr.Row():
        with gr.Column(scale=2):
            plot = gr.Plot()
        with gr.Column(scale=1):
            description = gr.Markdown()
            occurrences = gr.Markdown()

    sorties = [plot, description, occurrences]
    path_state.change(update_view, [path_state, vue_dd], sorties)
    vue_dd.change(update_view, [path_state, vue_dd], sorties)
    demo.load(update_view, [path_state, vue_dd], sorties)


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
