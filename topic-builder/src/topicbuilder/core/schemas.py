from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """
    A topic entry in the config, with an optional parent id for meta-topic grouping.
    """

    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str
    parent: UUID | None = None
    level: int = 0
    validated: bool = False


class Taxonomy(BaseModel):
    """
    Container for a list of topics, used as the shared config format across all tasks.
    """

    topics: list[Topic]


class Document(BaseModel):
    """
    A single row from the input CSV, identified by an id and carrying its text content.
    """

    id: str
    content: str


class Label(BaseModel):
    """
    A topic found in a specific text, with a justification and verbatim extract.
    """

    name: str
    rationale: str
    extract: str


class DocumentLabels(BaseModel):
    """
    The labels found for a single document.
    """

    id: str
    labels: list[Label]


class LabeledDataset(BaseModel):
    """
    Per-document label results produced by the label task.
    """

    documents: list[DocumentLabels]


class TopicMerge(BaseModel):
    """
    Records that several near-duplicate topics were collapsed into a single surviving topic.
    """

    sources: Taxonomy
    target: Topic


class ParentCandidate(BaseModel):
    """
    A proposed parent name together with candidate child topics, from the first parent pass.
    """

    parent: str
    children: Taxonomy


class ParentAddition(BaseModel):
    """
    Records that a new meta-topic was added as a parent for a group of existing topics.
    """

    parent: Topic
    children: Taxonomy


class FactorizeReport(BaseModel):
    """
    Change report produced by the factorize task describing topic merges.
    """

    merges: list[TopicMerge]


class ParentDiscoveryReport(BaseModel):
    """
    Change report produced by the structure task describing parent additions.
    """

    parents_added: list[ParentAddition]
