"""ListenBrainz submit-listens wire format.

https://listenbrainz.readthedocs.io/en/latest/users/api/core.html#post--1-submit-listens
Unknown fields are accepted (LB clients send many optional keys) but ignored.
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_LISTENS_PER_REQUEST = 1000
MAX_FIELD_LEN = 1000


class AdditionalInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    duration_ms: int | None = Field(default=None, ge=0, le=86_400_000)
    duration: float | None = Field(default=None, ge=0, le=86_400)  # seconds (Web Scrobbler)
    isrc: str | None = None
    recording_mbid: str | None = None
    release_mbid: str | None = None
    music_service: str | None = None
    music_service_name: str | None = None
    media_player: str | None = None
    submission_client: str | None = None
    submission_client_version: str | None = None
    origin_url: str | None = None
    spotify_id: str | None = None

    @field_validator(
        "isrc",
        "recording_mbid",
        "release_mbid",
        "music_service",
        "music_service_name",
        "media_player",
        "submission_client",
        "origin_url",
        "spotify_id",
        mode="before",
    )
    @classmethod
    def _short_str(cls, v: Any) -> Any:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("must be a string")
        if len(v) > MAX_FIELD_LEN:
            raise ValueError("too long")
        return v

    @property
    def effective_duration_ms(self) -> int | None:
        if self.duration_ms is not None:
            return self.duration_ms
        if self.duration is not None:
            return round(self.duration * 1000)
        return None

    @staticmethod
    def _uuid(v: str | None) -> UUID | None:
        try:
            return UUID(v) if v else None
        except ValueError:
            return None

    @property
    def recording_uuid(self) -> UUID | None:
        return self._uuid(self.recording_mbid)

    @property
    def release_uuid(self) -> UUID | None:
        return self._uuid(self.release_mbid)


class TrackMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")

    artist_name: str = Field(min_length=1, max_length=MAX_FIELD_LEN)
    track_name: str = Field(min_length=1, max_length=MAX_FIELD_LEN)
    release_name: str | None = Field(default=None, max_length=MAX_FIELD_LEN)
    additional_info: AdditionalInfo = Field(default_factory=AdditionalInfo)

    @field_validator("artist_name", "track_name")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v


class Listen(BaseModel):
    model_config = ConfigDict(extra="allow")

    listened_at: int | None = Field(default=None, ge=0)
    track_metadata: TrackMetadata


ListenType = Literal["single", "playing_now", "import"]


class Submission(BaseModel):
    listen_type: ListenType
    payload: list[Listen]

    @model_validator(mode="after")
    def _lb_rules(self) -> "Submission":
        n = len(self.payload)
        if n == 0:
            raise ValueError("payload must contain at least one listen")
        if self.listen_type in ("single", "playing_now") and n != 1:
            raise ValueError(f"listen_type {self.listen_type} requires exactly one listen")
        if n > MAX_LISTENS_PER_REQUEST:
            raise ValueError(f"too many listens: at most {MAX_LISTENS_PER_REQUEST} per request")
        for listen in self.payload:
            if self.listen_type == "playing_now" and listen.listened_at is not None:
                raise ValueError("playing_now listens must not have listened_at")
            # LB requires listened_at for single too; Jingle defaults it to receive time.
            if self.listen_type == "import" and listen.listened_at is None:
                raise ValueError("listened_at is required for import listens")
        return self
