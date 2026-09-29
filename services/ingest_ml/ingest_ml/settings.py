from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    jingle_env: str = "local"
    jingle_demo: bool = False
    database_url: str = "postgresql://jingle:jingle-local@localhost:5432/jingle"
    mongo_url: str = "mongodb://localhost:27017/jingle"
    redis_url: str = "redis://localhost:6379/0"
    service_token: str = "test-service-token"
    musicbrainz_user_agent: str = "Jingle/0.1 ( pilot )"
    listenbrainz_api_url: str = "https://api.listenbrainz.org"
    lastfm_api_key: str = ""
    lastfm_shared_secret: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = ""
    spotify_allowlist: str = ""


settings = Settings()
