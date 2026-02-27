from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Competitor Ad War Room"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/ad_war_room"

    meta_access_token: str = ""
    meta_app_id: str = ""
    meta_api_version: str = "v20.0"
    meta_base_url: str = "https://graph.facebook.com"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    default_country: str = "IN"
    default_ad_type: str = "ALL"
    request_timeout_seconds: int = 45

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
