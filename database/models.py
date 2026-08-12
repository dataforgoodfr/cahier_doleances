from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Contribution(Base):
    __tablename__ = "contribution"

    id = Column(Integer, primary_key=True)
    city = Column(
        String
    )  # parsée du nom du fichier ; TODO insee/table city si data INSEE
    pdf_file = Column(
        String
    )  # nom du fichier du cahier ; TODO ajuster en fonction de l'adaptation S3
    start_page = Column(Integer)
    end_page = Column(Integer)
    is_handwritten = Column(Boolean)


class Extraction(Base):
    __tablename__ = "extraction"

    id = Column(Integer, primary_key=True)
    contribution_id = Column(Integer, ForeignKey("contribution.id"))
    ocr = Column(String)
    text = Column(Text)
    num_words = Column(Integer)
    num_lines = Column(Integer)


class PageExtraction(Base):
    """Page-by-page extracted text with quality scoring and an OCR flag.

    One row per persisted PDF page. Metadata pages (first two) are not inserted
    here; they are only used to extract ``city``.
    """

    __tablename__ = "page_extraction"

    id = Column(Integer, primary_key=True)
    contribution_id = Column(Integer, ForeignKey("contribution.id"))
    pdf_name = Column(String)
    page_number = Column(Integer)
    text = Column(Text)  # texte extrait et nettoyé
    quality_score = Column(Float)  # 0.0 (garbage) à 1.0 (texte propre)
    needs_ocr = Column(Boolean)  # page manuscrite suspectée
    city = Column(String)  # ville extraite


# Référentiel des thèmes, alimenté depuis la livraison de l'équipe analyse.
class Topic(Base):
    __tablename__ = "topic"

    id = Column(Integer, primary_key=True)
    # UUID de la livraison : clé de rapprochement pour recharger sans dupliquer
    external_id = Column(String, unique=True)
    name = Column(String)
    description = Column(Text)
    level = Column(Integer)  # rang d'abstraction fourni par l'équipe analyse
    validated = Column(Boolean)  # relecture humaine du thème
    parent_id = Column(Integer, ForeignKey("topic.id"))  # hiérarchie
    parent = Column(Text)  # ancien parent par nom, remplacé par parent_id


class Instance(Base):
    __tablename__ = "instance"

    id = Column(Integer, primary_key=True)
    contribution_id = Column(Integer, ForeignKey("contribution.id"))
    # id du document dans la livraison analyse ; le rapprochement avec
    # contribution reste à faire, on conserve la clé source en attendant
    external_doc_id = Column(String)
    topic_id = Column(Integer, ForeignKey("topic.id"))
    verbatim = Column(Text)
    summary = Column(Text)


class Feeling(Base):
    __tablename__ = "feeling"

    id = Column(Integer, primary_key=True)
    contribution_id = Column(Integer, ForeignKey("contribution.id"))
    name = Column(String)


class Annotation(Base):
    __tablename__ = "annotation"

    contribution_id = Column(Integer, ForeignKey("contribution.id"), primary_key=True)
    is_anonymized = Column(Boolean)
    is_of_interest = Column(Boolean)
