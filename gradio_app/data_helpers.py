import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Constantes
ROOT = Path(__file__).resolve().parent.parent
PDF_DIR = ROOT / "data" / "raw" / "pdfs"

load_dotenv(ROOT / ".env")
engine = create_engine(
    URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
    ),
    pool_pre_ping=True,
)

def list_communes() -> list[str]:
    # la commune est parsée du PDF : elle est vide quand l'extraction a échoué.
    # On les écarte, sinon la vue s'ouvre sur une commune sans nom.
    q = text("""
        SELECT DISTINCT city FROM contribution
        WHERE city IS NOT NULL AND btrim(city) <> ''
        ORDER BY city
    """)
    return pd.read_sql(q, engine)["city"].tolist()

def ref_topic_counts() -> pd.DataFrame:
    """Nom + nombre d'instances par thème (dropdown et panneau de répartition)."""
    # LEFT JOIN : un thème sans instance reste visible (taxonomie ≠ avancement)
    q = text("""
        SELECT r.name, count(t.id) AS n
        FROM topic r
        LEFT JOIN instance t ON t.topic_id = r.id
        GROUP BY r.name
        ORDER BY r.name
    """)
    return pd.read_sql(q, engine)

def list_ref_topics() -> list[str]:
    """Libellés du dropdown thème : 'fiscalité (4)'."""
    return [f"{r.name} ({r.n})" for r in ref_topic_counts().itertuples()]

def topic_graph() -> pd.DataFrame:
    """Les topics avec leur parent et leur nombre d'instances (vue graphe)."""
    q = text("""
        SELECT r.name, r.parent, count(i.id) AS n
        FROM topic r
        LEFT JOIN instance i ON i.topic_id = r.id
        GROUP BY r.name, r.parent
        ORDER BY r.name
    """)
    return pd.read_sql(q, engine)

def topic_rows(name: str) -> pd.DataFrame:
    """Les instances d'un thème, jointes à leur contribution (vue 'Par thème')."""
    q = text("""
        SELECT k.city, k.pdf_file,
               (SELECT count(*) FROM contribution k2
                 WHERE k2.city = k.city AND k2.id <= k.id) AS pos,
               (SELECT count(*) FROM contribution k3
                 WHERE k3.city = k.city) AS total,
               (SELECT string_agg(name, ', ') FROM feeling
                 WHERE contribution_id = k.id) AS feelings,
               t.verbatim, t.summary, t.contribution_id
        FROM instance t
        JOIN topic r ON r.id = t.topic_id
        JOIN contribution k ON k.id = t.contribution_id
        WHERE r.name = :name
        ORDER BY k.city, k.id, t.id
    """)
    return pd.read_sql(q, engine, params={"name": name})

def _rows(commune: str) -> pd.DataFrame:
    """Les contributions d'une commune."""
    # une seule extraction affichée par contribution : la plus récente
    q = text("""
        SELECT k.id, k.city, k.pdf_file, k.start_page, k.end_page, k.is_handwritten,
               e.ocr, e.text, e.num_words, e.num_lines,
               a.is_anonymized, a.is_of_interest,
               (SELECT string_agg(r.name, ', ') FROM instance t
                 JOIN topic r ON r.id = t.topic_id
                 WHERE t.contribution_id = k.id) AS topics,
               (SELECT string_agg(name, ', ') FROM feeling
                 WHERE contribution_id = k.id) AS feelings
        FROM contribution k
        LEFT JOIN extraction e ON e.id = (
            SELECT max(id) FROM extraction WHERE contribution_id = k.id
        )
        LEFT JOIN annotation a ON a.contribution_id = k.id
        WHERE k.city = :city
        ORDER BY k.id
    """)
    return pd.read_sql(q, engine, params={"city": commune})

def _topic_instances(contribution_id: int) -> pd.DataFrame:
    """Les instances de thèmes d'une contribution avec verbatim et résumé."""
    q = text("""
        SELECT r.name, t.verbatim, t.summary
        FROM instance t JOIN topic r ON r.id = t.topic_id
        WHERE t.contribution_id = :cid
        ORDER BY t.id
    """)
    return pd.read_sql(q, engine, params={"cid": contribution_id})

def _int(value) -> str:
    """Entier en texte, ou 'N/C' si manquant."""
    return "N/C" if pd.isna(value) else str(int(value))

def _text(value) -> str:
    """Valeur texte, ou 'N/C' si manquante."""
    return "N/C" if pd.isna(value) else str(value)

def _bool(value) -> str:
    """Booléen en texte ('oui'/'non'), ou 'N/C' si manquant."""
    return "N/C" if pd.isna(value) else ("oui" if value else "non")

def _pages(start, end) -> str:
    """'2' ou '4-5', ou 'N/C' si manquant."""
    if pd.isna(start):
        return "N/C"
    if pd.isna(end) or int(end) == int(start):
        return str(int(start))
    return f"{int(start)}-{int(end)}"

def _nature(is_handwritten) -> str:
    if pd.isna(is_handwritten):
        return "N/C"
    return "Manuscrit" if is_handwritten else "Dactylographié"

def list_contributions(commune: str) -> list[str]:
    rows = _rows(commune)
    return [f"{i + 1}/{len(rows)} | {_nature(h)}" for i, h in enumerate(rows["is_handwritten"])]

def get_contribution(commune: str, idx: int) -> dict:
    rows = _rows(commune)
    r = rows.iloc[idx]
    # le détail (verbatim + résumé) ne s'affiche que si l'analyse existe
    inst = _topic_instances(int(r["id"]))
    details = "".join(
        f"\n  - **{i.name}** — « {i.verbatim} » : *{i.summary}*"
        for i in inst.itertuples() if pd.notna(i.verbatim)
    )
    return {
        # bloc affiché à gauche, sous le select Contribution
        "analyse": (
            f"#### Analyse textuelle\n"
            f"- **Thèmes détectés** : {_text(r['topics'])}{details}\n"
            f"- **Sentiment** : {_text(r['feelings'])}\n"
            f"- **Anonymisé** : {_bool(r['is_anonymized'])}\n"
            f"- **Contribution d'intérêt** : {_bool(r['is_of_interest'])}"
        ),
        # provenance technique, au-dessus du résultat OCR
        # (la nature Manuscrit/Dactylographié est déjà dans le libellé du dropdown)
        "header": (
            f"| Pages | Lignes | Mots | Extraction |\n"
            f"|---|---|---|---|\n"
            f"| {_pages(r['start_page'], r['end_page'])} | {_int(r['num_lines'])} "
            f"| {_int(r['num_words'])} | {_text(r['ocr'])} |"
        ),
        "text": r["text"] if pd.notna(r["text"]) else "N/C (pas encore extraite)",
        "pdf_file": r["pdf_file"],
        # état d'annotation existant (le tien ou celui d'un autre bénévole)
        "is_anonymized": bool(r["is_anonymized"]) if pd.notna(r["is_anonymized"]) else False,
        "is_of_interest": bool(r["is_of_interest"]) if pd.notna(r["is_of_interest"]) else False,
    }

def save_annotation(commune: str, idx: int, is_anonymized: bool, is_of_interest: bool) -> str:
    contribution_id = int(_rows(commune).iloc[idx]["id"])
    with engine.begin() as conn: # begin = transaction, commit automatique
        if not is_anonymized and not is_of_interest:
            # plus rien d'activé : on supprime la ligne (contribution redevient vierge)
            conn.execute(
                text("DELETE FROM annotation WHERE contribution_id = :cid"),
                {"cid": contribution_id},
            )
            return f"Annotation effacée (contribution {idx + 1})."
        # UPSERT : insère, ou met à jour l'annotation existante
        conn.execute(
            text("""
                INSERT INTO annotation (contribution_id, is_anonymized, is_of_interest)
                VALUES (:cid, :anonymized, :of_interest)
                ON CONFLICT (contribution_id) DO UPDATE
                   SET is_anonymized = EXCLUDED.is_anonymized,
                       is_of_interest = EXCLUDED.is_of_interest
            """),
            {"cid": contribution_id, "anonymized": is_anonymized,
             "of_interest": is_of_interest},
        )
    return f"Enregistré (contribution {idx + 1})."


#  vue graphe : la taxonomie et ses détections, lues une fois au démarrage
def charger_taxonomie() -> pd.DataFrame:
    """Tous les topics avec leur parent résolu par nom (les noms sont uniques)."""
    q = text("""
        SELECT t.id, t.external_id, t.name, t.description, t.level, p.name AS parent_nom
        FROM topic t
        LEFT JOIN topic p ON p.id = t.parent_id
    """)
    return pd.read_sql(q, engine)


def charger_detections() -> pd.DataFrame:
    """Les instances, rattachées au nom de leur topic.

    `external_doc_id` est l'identifiant du document dans la livraison analyse :
    le rapprochement avec `contribution` n'est pas résolu, on affiche cet id tel quel.
    """
    q = text("""
        SELECT t.name AS topic, i.verbatim, i.summary, i.external_doc_id
        FROM instance i
        JOIN topic t ON t.id = i.topic_id
        ORDER BY i.id
    """)
    return pd.read_sql(q, engine)
