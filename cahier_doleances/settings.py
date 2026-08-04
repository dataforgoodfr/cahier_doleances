import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

logger = logging.getLogger("cahier_doleances")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    db_host: str = ""
    db_port: str = ""
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""

    s3_url: str = ""
    s3_region: str = ""
    s3_endpoint: str = ""
    scw_access_key: str = ""
    scw_secret_key: str = ""
    s3_bucket_name: str = ""

    path_to_data: str = ""
    log_level: str = "INFO"


settings = Settings()
