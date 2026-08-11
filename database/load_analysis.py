"""Charge la livraison de l'équipe analyse (taxonomy + instances) en base.

Idempotent : rejouable sans dupliquer. `topic` est un référentiel, il se
synchronise par `external_id` (upsert) et ne se vide jamais. Les `instance`
sont en revanche remplacées à chaque exécution : elles dépendent entièrement
de la livraison, et rien d'autre ne les alimente aujourd'hui.

Le rapprochement document -> contribution n'est pas résolu (3441 contributions
en base pour 1524 documents livrés) : `contribution_id` reste NULL et l'id
source est conservé dans `external_doc_id` pour pouvoir le faire plus tard.

Lancer :  uv run python -m database.load_analysis [chemin/vers/analysis_v4]
"""

import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from database.db import get_engine
from database.models import Instance, Topic

DEFAUT = Path(__file__).resolve().parent.parent / "analyse" / "analysis_v4"


def _propre(valeur):
    """Retire les caractères NUL : PostgreSQL les refuse en text.

    La livraison en contient dans les noms, descriptions, extraits et
    justifications. On nettoie AUSSI le nom côté label, sinon il ne
    correspondrait plus au nom nettoyé du topic et la jointure casserait.
    """
    return valeur.replace("\x00", "") if isinstance(valeur, str) else valeur


def charger_topics(session: Session, topics: list[dict]) -> dict[str, int]:
    """Upsert des topics par external_id. Renvoie {external_id: topic.id}."""
    connus = {t.external_id: t for t in session.query(Topic).all() if t.external_id}
    for t in topics:
        ligne = connus.get(t["id"])
        if ligne is None:
            ligne = Topic(external_id=t["id"])
            session.add(ligne)
            connus[t["id"]] = ligne
        ligne.name = _propre(t["name"])
        ligne.description = _propre(t["description"])
        ligne.level = t["level"]
        ligne.validated = t["validated"]
    session.flush()  # attribue les id auto-incrémentés
    return {ext: ligne.id for ext, ligne in connus.items()}


def rattacher_parents(session: Session, topics: list[dict], ids: dict[str, int]) -> int:
    """Deuxième passe : `parent` est un UUID, il faut que tous les topics existent."""
    orphelins = 0
    par_ext = {t.external_id: t for t in session.query(Topic).all() if t.external_id}
    for t in topics:
        parent_ext = t.get("parent")
        cible = ids.get(parent_ext) if parent_ext else None
        if parent_ext and cible is None:
            orphelins += 1  # parent absent de la livraison
        par_ext[t["id"]].parent_id = cible
    session.flush()
    return orphelins


def charger_instances(session: Session, documents: list[dict], ids_par_nom: dict[str, int]) -> int:
    """Remplace toutes les instances par celles de la livraison."""
    session.execute(text("DELETE FROM instance"))
    inconnus = 0
    for doc in documents:
        for lab in doc["labels"]:
            topic_id = ids_par_nom.get(_propre(lab["name"]))
            if topic_id is None:
                inconnus += 1
                continue
            session.add(Instance(
                contribution_id=None,          # rapprochement non résolu
                external_doc_id=str(doc["id"]),
                topic_id=topic_id,
                verbatim=_propre(lab["extract"]),
                summary=_propre(lab["rationale"]),
            ))
    return inconnus


def main(dossier: Path = DEFAUT) -> None:
    topics = json.loads((dossier / "taxonomy.json").read_text())["topics"]
    documents = json.loads((dossier / "instances.json").read_text())["documents"]
    print(f"livraison : {len(topics)} topics · {len(documents)} documents")

    with Session(get_engine()) as session:
        ids = charger_topics(session, topics)
        print(f"  topics synchronisés : {len(ids)}")

        orphelins = rattacher_parents(session, topics, ids)
        print(f"  parents rattachés ({orphelins} parent(s) introuvable(s) -> NULL)")

        ids_par_nom = {t.name: t.id for t in session.query(Topic).all()}
        inconnus = charger_instances(session, documents, ids_par_nom)
        print(f"  instances chargées ({inconnus} label(s) sans topic -> ignoré(s))")

        session.commit()

        for modele in (Topic, Instance):
            print(f"{modele.__tablename__}: {session.query(modele).count()} lignes")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAUT)
