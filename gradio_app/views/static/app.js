// Le serveur renvoie l'état complet (figure, panneau, sélecteurs) ; on l'affiche.

let CONFIG = { apercu: "", strates: [] };
let strate = null;

const $ = (id) => document.getElementById(id);
const etat = (texte) => { $("etat").textContent = texte; };

async function poste(route, corps) {
  const r = await fetch(route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
  if (!r.ok) throw new Error(`${route} → HTTP ${r.status}`);
  return r.json();
}

// --- ligne de sélecteurs ---
function dessineBarre(niveaux) {
  const barre = $("barre");
  barre.innerHTML = "";
  barre.appendChild(
    champ("Strate d'entrée", CONFIG.strates, strate, (v) => chargeApercu(v)),
  );
  for (const niveau of niveaux) {
    barre.appendChild(
      champ(niveau.label, niveau.options, niveau.value, (v) => {
        if (!v || v === CONFIG.apercu) chargeApercu(strate);
        else chargeNoeud(v);
      }),
    );
  }
}

// options : ["texte"] ou [{value, label}]
function champ(label, options, valeur, surChangement) {
  const bloc = document.createElement("div");
  bloc.className = "champ";

  const lab = document.createElement("label");
  lab.textContent = label;

  const sel = document.createElement("select");
  if (valeur === null) {
    const vide = document.createElement("option");
    vide.value = "";
    vide.textContent = "—";
    sel.appendChild(vide);
  }
  for (const o of options) {
    const objet = o && typeof o === "object";
    const opt = document.createElement("option");
    opt.value = objet ? o.value : o;
    opt.textContent = objet ? o.label : o;
    opt.title = opt.textContent;
    if (opt.value === valeur) opt.selected = true;
    sel.appendChild(opt);
  }
  sel.onchange = (e) => surChangement(e.target.value);

  bloc.append(lab, sel);
  return bloc;
}

// --- graphe ---
function dessineGraphe(figure) {
  const gd = $("graphe");
  Plotly.react(gd, figure.data, figure.layout, {
    responsive: true,
    displaylogo: false,
  });
  // Plotly.react garde les écouteurs : on purge avant de rebrancher
  if (gd.removeAllListeners) gd.removeAllListeners("plotly_click");
  gd.on("plotly_click", (ev) => {
    const nom = ev.points[0].customdata;
    if (nom) chargeNoeud(nom);
  });
}

// --- rendu ---
function applique(reponse) {
  if (reponse.erreur) {
    etat(reponse.erreur);
    return;
  }
  strate = reponse.strate;
  dessineGraphe(reponse.figure);
  dessineBarre(reponse.niveaux);
  $("panneau").innerHTML = reponse.description + reponse.occurrences;
}

async function chargeApercu(cle) {
  strate = cle;
  etat(`Strate ${cle} — clique un nœud pour entrer dedans.`);
  applique(await poste("/graphe/api/apercu", { strate: cle }));
}

async function chargeNoeud(nom) {
  etat(`Sélection : ${nom}`);
  applique(await poste("/graphe/api/noeud", { nom }));
}

async function demarre() {
  CONFIG = await (await fetch("/graphe/api/config")).json();
  await chargeApercu(CONFIG.strates[0].value);
}

demarre().catch((e) => etat(`Erreur : ${e.message}`));
