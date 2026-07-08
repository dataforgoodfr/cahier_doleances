"""SQLModel schema for the cahiers database.

    Contribution --> City        (many-to-one, FK city_id)
    Contribution --> Pdf         (many-to-one, FK pdf_id)
    Contribution --> OcrModel    (many-to-one, FK ocr_id)
    Contribution <-> Topic       (many-to-many, via contribution_topic)
    Contribution <-> Feeling     (many-to-many, via contribution_feeling)

On ``Contribution`` the foreign keys and the scalar metadata fields
(``start_page``, ``num_page``, ``num_words``, ``num_lines``,
``is_handwritten``) are nullable so partial contributions can be loaded;
only ``text`` is required. On the reference tables the required columns are
``name`` / ``filename``, plus City's ``insee`` and ``department``
(``population`` is optional). Tighten or relax these with a new migration as
the data evolves.
"""

from sqlalchemy import Column, Text
from sqlmodel import Field, Relationship, SQLModel


# --------------------------------------------------------------------------- #
# Many-to-many link tables
# --------------------------------------------------------------------------- #
class ContributionTopic(SQLModel, table=True):
    __tablename__ = "contribution_topic"

    contribution_id: int = Field(foreign_key="contribution.id", primary_key=True)
    topic_id: int = Field(foreign_key="topic.id", primary_key=True)


class ContributionFeeling(SQLModel, table=True):
    __tablename__ = "contribution_feeling"

    contribution_id: int = Field(foreign_key="contribution.id", primary_key=True)
    feeling_id: int = Field(foreign_key="feeling.id", primary_key=True)


# --------------------------------------------------------------------------- #
# Main tables
# --------------------------------------------------------------------------- #
class City(SQLModel, table=True):
    __tablename__ = "city"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    insee: str  # INSEE code, e.g. "17300" / "2A004" — text, keeps leading zeros
    population: int | None = None
    department: str  # department code, e.g. "17" / "01" / "2A"

    contributions: list["Contribution"] = Relationship(back_populates="city")


class Pdf(SQLModel, table=True):
    __tablename__ = "pdf"

    id: int | None = Field(default=None, primary_key=True)
    filename: str

    contributions: list["Contribution"] = Relationship(back_populates="pdf")


class OcrModel(SQLModel, table=True):
    __tablename__ = "ocr_model"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    contributions: list["Contribution"] = Relationship(back_populates="ocr")


class Topic(SQLModel, table=True):
    __tablename__ = "topic"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    contributions: list["Contribution"] = Relationship(
        back_populates="topics", link_model=ContributionTopic
    )


class Feeling(SQLModel, table=True):
    __tablename__ = "feeling"

    id: int | None = Field(default=None, primary_key=True)
    name: str

    contributions: list["Contribution"] = Relationship(
        back_populates="feeling", link_model=ContributionFeeling
    )


class Contribution(SQLModel, table=True):
    __tablename__ = "contribution"

    id: int | None = Field(default=None, primary_key=True)
    text: str = Field(sa_column=Column(Text, nullable=False))

    city_id: int | None = Field(default=None, foreign_key="city.id")
    pdf_id: int | None = Field(default=None, foreign_key="pdf.id")
    ocr_id: int | None = Field(default=None, foreign_key="ocr_model.id")

    start_page: int | None = None
    num_page: int | None = 1
    num_words: int | None = None
    num_lines: int | None = None
    is_handwritten: bool | None = None

    city: City | None = Relationship(back_populates="contributions")
    pdf: Pdf | None = Relationship(back_populates="contributions")
    ocr: OcrModel | None = Relationship(back_populates="contributions")
    topics: list[Topic] = Relationship(
        back_populates="contributions", link_model=ContributionTopic
    )
    feeling: list[Feeling] = Relationship(
        back_populates="contributions", link_model=ContributionFeeling
    )
