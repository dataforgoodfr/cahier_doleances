"""Configuration technique du module d'extraction (lue depuis `.env`).

Ne contient que ce dont l'extraction a besoin : la connexion PostgreSQL reste
construite par `database/db.py`, qui appartient au modèle de données partagé.
Les paramètres métier de l'extraction (seuils, marqueurs) sont dans `config.py`.
"""

import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Dossier local contenant les PDFs à traiter.
    path_to_data: str = ""
    log_level: str = "INFO"


settings = Settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("extraction.without_ocr")
