from sqlalchemy.orm import Session

from cahier_doleances.database.db import get_engine
from cahier_doleances.database.models import (
    Annotation,
    Contribution,
    Extraction,
    Feeling,
    Instance,
    Topic,
)

OCR = "mock_data_ocr"

MOCK = [
    {
        "city": "Trizay",
        "pdf_file": "Cahier-de-doleances-de-Trizay-transcription.pdf",
        "start_page": 2,
        "end_page": 3,
        "is_handwritten": False,
        "text": (
            "- Régler en priorité absolue le problème des SDF plutôt que d'en créer "
            "de nouveaux.\n"
            "- Suppression de la taxe carbone, la faire payer aux pollueurs "
            "(compagnies aériennes, grosses industries).\n"
            "- Redonner aux retraités leur pouvoir d'achat (indexation de toutes les "
            "retraites sur l'inflation et suppression des 1,7 de CSG pour tous).\n"
            "- Rétablissement de l'ISF.\n"
            "- Suppression de toutes les niches fiscales.\n"
            "- Suppression de la TVA sur la TVA.\n"
            "- Taxation majorée des produits de luxe.\n"
            "- Vote obligatoire et prise en compte des votes blancs.\n"
            "- Casier judiciaire vierge pour TOUS LES ÉLUS.\n"
            "- Révision de la Constitution par voie référendaire.\n"
            "- Politique migratoire plus stricte.\n"
            "- Séparation des pouvoirs : ÉTAT/JUSTICE.\n"
            "- Suppression des avantages non taxés, non imposables versés aux élus, "
            "hauts fonctionnaires et autres.\n"
            "- Reconsidération des avantages accordés par bon nombre de sociétés : "
            "SNCF, EDF, compagnies aériennes, etc., facilitant ainsi une baisse des tarifs."
        ),
        "topics": [
            {
                "name": "fiscalité",
                "verbatim": "Rétablissement de l'ISF.",
                "summary": "Retour de l'ISF, suppression des niches fiscales, taxation du luxe.",
            },
            {
                "name": "pouvoir d'achat",
                "verbatim": "Redonner aux retraités leur pouvoir d'achat (indexation de toutes les retraites sur l'inflation et suppression des 1,7 de CSG pour tous).",
                "summary": "Indexer les retraites sur l'inflation, alléger la CSG.",
            },
            {
                "name": "démocratie",
                "verbatim": "Vote obligatoire et prise en compte des votes blancs.",
                "summary": "Vote obligatoire, vote blanc reconnu, révision par référendum.",
            },
        ],
        "feeling": "détermination",
    },
    {
        "city": "Échebrune",
        "pdf_file": "Cahier-de-doleances-dEchebrune-transcription.pdf",
        "start_page": 2,
        "end_page": 3,
        "is_handwritten": False,
        "text": (
            "Afin de faire diminuer le « train de vie » de notre GRAND PAYS et pouvoir "
            "respecter les engagements pris, vis à vis de l'Europe :\n"
            "I - Diminution des nombres de députés et des 1 132 fonctionnaires de "
            "l'Assemblée nationale (6 400,00 €/nets/mois avec prime salaire de base "
            "pour un agent d'étage - exemple qui distribue le courrier).\n"
            "II - Suppression du Sénat.\n"
            "III - Diminution des rémunérations des 600 hauts fonctionnaires de l'État "
            "(18 700 €/mois).\n"
            "IV - Diminuer les avantages liés à la fonction qui ne devraient être "
            "accordés qu'au seul titulaire (uniquement pendant son mandat) et non pas "
            "à toute la famille !!!\n"
            "Au niveau régional :\n"
            "A - Éviter d'augmenter le nombre d'agents lorsqu'il y a regroupement de "
            "moyens (ex. : région Nouvelle-Aquitaine) ; il faut savoir se séparer des "
            "postes en doublon (comme un dirigeant le ferait dans sa propre entreprise).\n"
            "B - Regroupement des petites communes de moins de 1000 habitants. À ce "
            "jour il existe 34 977 communes ; celles qui ont fusionné ont vu leur "
            "dotation plus importante que si elles étaient restées séparées."
        ),
        "topics": [
            {
                "name": "dépenses publiques",
                "verbatim": "Diminution des rémunérations des 600 hauts fonctionnaires de l'État (18 700 €/mois).",
                "summary": "Réduire le train de vie de l'État : députés, hauts fonctionnaires, avantages.",
            },
            {
                "name": "démocratie",
                "verbatim": "II - Suppression du Sénat.",
                "summary": "Réforme institutionnelle : moins de députés, suppression du Sénat.",
            },
        ],
        "feeling": "septiscisme",
    },
    {
        "city": "Fontenet",
        "pdf_file": "Cahier-de-doleances-de-Fontenet-transcription.pdf",
        "start_page": 3,
        "end_page": 4,
        "is_handwritten": False,
        "text": (
            "Au fronton de nos mairies, parfois de nos écoles, est inscrit :\n"
            "Liberté, Égalité et Fraternité.\n"
            "De nos jours, cette phrase a-t-elle toujours la même valeur, a-t-elle un "
            "sens pour nos élus ?\n"
            "Est-il normal que des citoyens ne puissent vivre correctement du fruit de "
            "leur travail ? Des salariés en C.D.I. (et encore ils ont un contrat) ne "
            "peuvent parfois pas se loger tant exorbitants sont les loyers, et en "
            "nombre insuffisant. Est-il normal que certaines villes préfèrent payer "
            "des amendes plutôt que de construire des logements sociaux (honte à eux).\n"
            "Est-il normal que nos agriculteurs ou producteurs vendent à perte leurs "
            "produits ? Et ne puissent vivre de leur labeur ?\n"
            "Dans les moments difficiles que nous vivons, que penser des nombreux "
            "avantages que cumulent nos élus (cumul des mandats, cumul des salaires, "
            "des indemnités et avantages en nature de toutes sortes, retraites…\n"
            "Il est scandaleux que les anciens élus conservent des avantages alors "
            "qu'ils n'ont plus les prérogatives (voitures de fonction, personnel de "
            "sécurité et secrétariat…), nous faisons garder des propriétés d'anciens "
            "élus (président, ministre) à grand frais par les gendarmes ou autres.\n"
            "Quand nous savons que certains ne peuvent financièrement et sans "
            "« à côté » finir leur mois, cela sort de l'entendement.\n"
            "Nos élus fuient le terrain pour ne pas voir, entendre, sentir cette "
            "colère qui monte.\n"
            "Le petit peuple en a assez d'être « la vache à lait » de certains, "
            "toujours plus de taxes pour combler des déficits engagés et qui profitent "
            "toujours qu'à un petit nombre, ou régler les âneries faites par d'autres.\n"
            "Il me semblait qu'en 1789, le peuple français avait aboli les "
            "privilèges !!!\n"
            "Faudra-t-il recommencer ?"
        ),
        "topics": [
            {
                "name": "logement",
                "verbatim": "Des salariés en C.D.I. (et encore ils ont un contrat) ne peuvent parfois pas se loger tant exorbitants sont les loyers, et en nombre insuffisant.",
                "summary": "Loyers trop chers, manque de logements sociaux.",
            },
            {
                "name": "agriculture",
                "verbatim": "Est-il normal que nos agriculteurs ou producteurs vendent à perte leurs produits ?",
                "summary": "Les agriculteurs vendent à perte et ne vivent pas de leur travail.",
            },
            {
                "name": "démocratie",
                "verbatim": "Il me semblait qu'en 1789, le peuple français avait aboli les privilèges !!!",
                "summary": "Dénonce les privilèges et avantages cumulés des élus.",
            },
            {
                "name": "fiscalité",
                "verbatim": "toujours plus de taxes pour combler des déficits engagés",
                "summary": "Ras-le-bol fiscal du « petit peuple ».",
            },
        ],
        "feeling": "colère",
    },
    {
        "city": "Fontenet",
        "pdf_file": "Cahier-de-doleances-de-Fontenet-transcription.pdf",
        "start_page": 4,
        "end_page": 4,
        "is_handwritten": False,
        "text": (
            "Je suis solidaire du mouvement des Gilets jaunes et je suis en accord "
            "avec l'ensemble de leurs doléances concernant les taxes, perte du niveau "
            "de vie, diminution des retraites.\n"
            "Je pense que pour être citoyen à part entière, il est important que toute "
            "personne vivant sur le territoire français paye l'impôt selon ses "
            "revenus, les plus défavorisés 1 € par mois, donc 12 € par an… Fini "
            "l'assistanat. Soyons fier d'être citoyen français. Pour les plus aisés "
            "revenons à l'ISF.\n"
            "Égalité en droits et en devoirs\n"
            "Autre proposition :\n"
            "Au lieu de verser une allocation « rentrée » qui malheureusement ne sert "
            "pas forcément aux enfants mais à payer des arriérés de factures, la vie "
            "est dure pour certains… Mettons la cantine gratuite à tous ces enfants "
            "scolarisés. Au moins, chacun aura un repas équilibré et chaud par jour.\n"
            "Égalité en droits et en devoirs\n"
            "On s'aperçoit que nos présidents, une fois élu, oublient leurs promesses "
            "ou les remettent à plus tard, à la fin de leur quinquennat.\n"
            "Mettons en place le Référendum d'Initiative Citoyen. La parole doit être "
            "donnée au peuple, pas seulement aux élus.\n"
            "Égalité en droits et en devoirs"
        ),
        "topics": [
            {
                "name": "fiscalité",
                "verbatim": "il est important que toute personne vivant sur le territoire français paye l'impôt selon ses revenus",
                "summary": "Impôt pour tous selon les revenus ; retour de l'ISF pour les plus aisés.",
            },
            {
                "name": "éducation",
                "verbatim": "Mettons la cantine gratuite à tous ces enfants scolarisés.",
                "summary": "Cantine gratuite pour tous les enfants scolarisés.",
            },
            {
                "name": "démocratie",
                "verbatim": "Mettons en place le Référendum d'Initiative Citoyen.",
                "summary": "Instaurer le RIC : donner la parole au peuple.",
            },
        ],
        "feeling": "espoir",
    },
]


def main():
    with Session(get_engine()) as session:
        # garde-fou : les ids étant auto-incrémentés, relancer le seed dupliquerait tout
        if session.query(Contribution).first():
            raise SystemExit("La base contient déjà des contributions : abandon.")

        # référentiel : un nom unique par thème (remplaçable par la liste
        # officielle de l'équipe analyse, sans migration) ; parent reste NULL,
        # la hiérarchie de la taxonomie sera fournie par l'équipe analyse
        names = sorted({t["name"] for entry in MOCK for t in entry["topics"]})
        refs = {}
        for name in names:
            ref = Topic(name=name)
            session.add(ref)
            session.flush()  # récupère l'id auto-généré
            refs[name] = ref.id

        for entry in MOCK:
            contribution = Contribution(
                city=entry["city"],
                pdf_file=entry["pdf_file"],
                start_page=entry["start_page"],
                end_page=entry["end_page"],
                is_handwritten=entry["is_handwritten"],
            )
            session.add(contribution)
            session.flush()  # récupère l'id auto-généré tout de suite

            # num_words / num_lines calculés depuis le texte : toujours cohérents
            session.add(
                Extraction(
                    contribution_id=contribution.id,
                    ocr=OCR,
                    text=entry["text"],
                    num_words=len(entry["text"].split()),
                    num_lines=entry["text"].count("\n") + 1,
                )
            )

            for t in entry["topics"]:
                session.add(
                    Instance(
                        contribution_id=contribution.id,
                        topic_id=refs[t["name"]],
                        verbatim=t["verbatim"],
                        summary=t["summary"],
                    )
                )
            session.add(Feeling(contribution_id=contribution.id, name=entry["feeling"]))

        session.commit()

        for model in (Contribution, Extraction, Topic, Instance, Feeling, Annotation):
            print(f"{model.__tablename__}: {session.query(model).count()} lignes")


if __name__ == "__main__":
    main()
