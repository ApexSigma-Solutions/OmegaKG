from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    secret_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Usage example:
# settings = Settings()
# print(settings.database_url)
