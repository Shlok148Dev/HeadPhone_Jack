from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Known non-secret service tokens (code default, .env.example); refused outside local/test.
_KNOWN_SERVICE_TOKENS = frozenset(
    {"test-service-token", "dev-only-change-me-service-token-0000000000000"}
)
_DEV_ENVS = frozenset({"local", "test"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", env_ignore_empty=True)

    jingle_env: str = "local"
    jingle_demo: bool = False
    database_url: str = "postgresql://jingle:jingle-local@localhost:5432/jingle"
    mongo_url: str = "mongodb://localhost:27017/jingle"
    redis_url: str = "redis://localhost:6379/0"
    service_token: str = "test-service-token"  # noqa: S105 - dev default; refused in prod
    # MusicBrainz requires a contact in the User-Agent; empty ⇒ lookups disabled (ADR-0016)
    musicbrainz_contact: str = ""
    # None = automatic: on, except in demo mode and tests. Set MUSICBRAINZ_ENABLED to force.
    musicbrainz_enabled: bool | None = None
    musicbrainz_api_url: str = "https://musicbrainz.org/ws/2"
    # Share of the global 1 req/s MusicBrainz budget one user may use (lookups per minute)
    musicbrainz_user_lookups_per_minute: int = 10
    # Per-user push budgets: requests per minute, and listens per hour (a request costs its
    # listen count), plus failed-auth requests per client IP per minute.
    push_rate_limit_per_minute: int = 60
    push_listen_limit_per_hour: int = 10_000
    push_auth_fail_limit_per_minute: int = 30
    listenbrainz_api_url: str = "https://api.listenbrainz.org"
    lastfm_api_key: str = ""
    lastfm_shared_secret: str = ""
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = ""
    spotify_allowlist: str = ""

    @model_validator(mode="after")
    def _refuse_weak_service_token(self) -> "Settings":
        if self.jingle_env in _DEV_ENVS:
            return self
        tok = self.service_token
        if tok in _KNOWN_SERVICE_TOKENS or tok.startswith("dev-only-") or len(tok) < 32:
            raise ValueError(
                "SERVICE_TOKEN must be set to a random value of at least 32 characters "
                f"when JINGLE_ENV={self.jingle_env!r}"
            )
        return self

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
