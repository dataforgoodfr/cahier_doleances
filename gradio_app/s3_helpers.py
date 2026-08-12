import os
import re
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

EXPIRATION = 3600  # durée de validité d'une URL présignée, en secondes


def _region() -> str:
    """Région S3. `S3_REGION` vaut parfois encore la valeur d'exemple :
    dans ce cas on la déduit de l'endpoint (https://s3.fr-par.scw.cloud)."""
    region = os.environ.get("S3_REGION", "")
    if region and region != "S3_REGION":
        return region
    trouve = re.search(r"s3\.([a-z]{2}-[a-z]{3})\.", os.environ.get("S3_ENDPOINT", ""))
    return trouve.group(1) if trouve else "fr-par"


@lru_cache(maxsize=1)
def _client():
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT"],
        region_name=_region(),
        aws_access_key_id=os.environ["SCW_ACCESS_KEY"],
        aws_secret_access_key=os.environ["SCW_SECRET_KEY"],
    )


@lru_cache(maxsize=1)
def index_pdf() -> dict[str, str]:
    """{nom de fichier: clé S3 complète}. Construit une fois, au premier appel.

    Renvoie un index vide si S3 est injoignable ou mal configuré : l'app doit
    rester utilisable sans les PDF.
    """
    bucket = os.environ.get("S3_BUCKET_NAME")
    if not bucket:
        return {}
    try:
        index = {}
        pages = _client().get_paginator("list_objects_v2").paginate(Bucket=bucket)
        for page in pages:
            for obj in page.get("Contents", []):
                cle = obj["Key"]
                if cle.lower().endswith(".pdf"):
                    index[cle.rsplit("/", 1)[-1]] = cle
        return index
    except (BotoCoreError, ClientError, KeyError):
        return {}


def url_pdf(nom_fichier: str | None) -> str | None:
    """URL temporaire vers le PDF, ou None s'il est introuvable."""
    if not nom_fichier:
        return None
    cle = index_pdf().get(nom_fichier)
    if cle is None:
        return None
    try:
        return _client().generate_presigned_url(
            "get_object",
            Params={"Bucket": os.environ["S3_BUCKET_NAME"], "Key": cle},
            ExpiresIn=EXPIRATION,
        )
    except (BotoCoreError, ClientError, KeyError):
        return None
