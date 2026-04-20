from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str
    APP_ENV: str
    APP_DEBUG: bool
    APP_HOST: str
    APP_PORT: int

    DB_HOST: str 
    DB_PORT: int 
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    DIRECTORY_PATH_STATIC_FILE:str
    DIRECTORY_PATH_TEMPLATE_FILE:str
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )
    
    @property
    def static_path(self) -> Path:
        return Path(self.DIRECTORY_PATH_STATIC_FILE)
    @property
    def template_path(self) ->Path:
        return Path(self.DIRECTORY_PATH_TEMPLATE_FILE)


settings = Settings()