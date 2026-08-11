import csv
import json
from pathlib import Path

from pydantic import BaseModel

from topicbuilder.core.schemas import Document, LabeledDataset, Taxonomy


def read_text(path: Path) -> str:
    """
    Read a UTF-8 text file and return its contents as a string.
    """
    return path.read_text(encoding="utf-8")


def read_texts(folder: Path) -> list[str]:
    """
    Read all .txt and .md files in `folder` and return their contents as a list of strings.
    """
    paths = sorted(p for ext in ("*.txt", "*.md") for p in folder.glob(ext))
    return [read_text(p) for p in paths]


def read_dataset(path: Path) -> list[Document]:
    """
    Read a CSV file with 'id' and 'content' columns and return a list of Documents.
    """
    with path.open(encoding="utf-8", newline="") as f:
        return [Document(id=row["id"], content=row["content"]) for row in csv.DictReader(f)]


def read_taxonomy(path: Path) -> Taxonomy:
    """
    Read a JSON topics config file and return a validated TopicConfig object.
    """
    with path.open(encoding="utf-8") as f:
        return Taxonomy.model_validate(json.load(f))


def read_labeled_dataset(path: Path) -> LabeledDataset:
    """
    Read a JSON labeled-dataset file and return a validated LabeledDataset object.
    """
    with path.open(encoding="utf-8") as f:
        return LabeledDataset.model_validate(json.load(f))


def write_json(obj: BaseModel, path: Path) -> None:
    """
    Serialize any Pydantic model as indented JSON and write to `path`, creating parent directories.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj.model_dump(mode="json"), f, indent=2)
    return
