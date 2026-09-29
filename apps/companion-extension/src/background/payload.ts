import { MUSIC_SERVICE, type TrackState } from "../shared/types";
import { SUBMISSION_CLIENT, VERSION } from "../shared/version";

/** ListenBrainz `submit-listens` body (https://listenbrainz.readthedocs.io/en/latest/users/json.html). */
export interface LbSubmission {
  listen_type: "single" | "playing_now";
  payload: [LbListen];
}

export interface LbListen {
  listened_at?: number;
  track_metadata: {
    artist_name: string;
    track_name: string;
    release_name?: string;
    additional_info: {
      music_service: string;
      origin_url?: string;
      duration_ms?: number;
      submission_client: string;
      submission_client_version: string;
    };
  };
}

export function buildSubmission(kind: "single" | "playing_now", track: TrackState, listenedAt?: number): LbSubmission {
  const info: LbListen["track_metadata"]["additional_info"] = {
    music_service: MUSIC_SERVICE[track.platform],
    submission_client: SUBMISSION_CLIENT,
    submission_client_version: VERSION,
  };
  if (track.originUrl) info.origin_url = track.originUrl;
  if (track.durationMs !== undefined) info.duration_ms = track.durationMs;

  const listen: LbListen = {
    track_metadata: {
      artist_name: track.artist,
      track_name: track.title,
      ...(track.album ? { release_name: track.album } : {}),
      additional_info: info,
    },
  };
  if (kind === "single") {
    if (listenedAt === undefined) throw new Error("single listens need listened_at");
    listen.listened_at = listenedAt;
  }
  return { listen_type: kind, payload: [listen] };
}
