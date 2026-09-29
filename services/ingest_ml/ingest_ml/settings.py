from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", env_ignore_empty=True)

    jingle_env: str = "local"
    jingle_demo: bool = False
    database_url: str = "postgresql://jingle:jingle-local@localhost:5432/jingle"
    mongo_url: str = "mongodb://localhost:27017/jingle"
    redis_url: str = "redis://localhost:6379/0"
    service_token: str = "test-service-token"  # noqa: S105 - overridden by SERVICE_TOKEN
    musicbrainz_user_agent: str = "Jingle/0.1 ( pilot )"  # legacy; UA is built from the contact
    # MusicBrainz requires a contact in the User-Agent; empty ⇒ lookups disabled (ADR-0013..0016)
    musicbrainz_contact: str = ""
    # None = automatic: on, except in demo mode and tests. Set MUSICBRAINZ_ENABLED to force.
    musicbrainz_enabled: bool | None = None
    musicbrainz_api_url: str = "https://musicbrainz.org/ws/2"
    # Per scrobble-token request budget on /ingest/1/* (token bucket, requests per minute)
    push_rate_limit_per_minute: int = 60
    listenbrainz_api_url: str = "https://api.listenbrainz.org"
    lastfm_api_key: str = ""
    lastfm_shared_secret: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = ""
    spotify_allowlist: str = ""

    @property
    def musicbrainz_active(self) -> bool:
        """Off without a contact; off in demo mode and tests unless explicitly enabled."""
        if not self.musicbrainz_contact.strip():
            return False
        if self.musicbrainz_enabled is not None:
            return self.musicbrainz_enabled
        return not self.jingle_demo and self.jingle_env != "test"

    @property
    def musicbrainz_ua(self) -> str:
        return f"Jingle/0.1 ( {self.musicbrainz_contact.strip()} )"


settings = Settings()
