package app.jingle.android

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.concurrent.Executors

/** POST {JINGLE_URL}/ingest/1/submit-listens (ListenBrainz format): the same route as the extension. */
object Submitter {
    private val io = Executors.newSingleThreadExecutor()

    fun send(ctx: Context, kind: String, t: Track, listenedAt: Long? = null) {
        val token = TokenStore.get(ctx) ?: return
        val info = JSONObject()
            .put("music_service", t.service)
            .put("submission_client", "Jingle Android")
            .put("submission_client_version", BuildConfig.VERSION_NAME)
        if (t.durationMs > 0) info.put("duration_ms", t.durationMs)
        val meta = JSONObject().put("artist_name", t.artist).put("track_name", t.title).put("additional_info", info)
        if (!t.album.isNullOrBlank()) meta.put("release_name", t.album)
        val listen = JSONObject().put("track_metadata", meta)
        if (listenedAt != null) listen.put("listened_at", listenedAt)
        val body = JSONObject().put("listen_type", kind).put("payload", JSONArray().put(listen)).toString()
        io.execute {
            try {
                val c = URL("${BuildConfig.JINGLE_URL}/ingest/1/submit-listens").openConnection() as HttpURLConnection
                c.requestMethod = "POST"
                c.connectTimeout = 10_000
                c.readTimeout = 10_000
                c.doOutput = true
                c.setRequestProperty("Authorization", "Token $token")
                c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write(body.toByteArray()) }
                // 401: the token was revoked (disconnected in Jingle). Forget it until paired again.
                if (c.responseCode == 401) TokenStore.clear(ctx)
                c.disconnect()
            } catch (_: Exception) {
                // Offline: this signal is skipped; the next one goes through. (No retry queue in v0.1.)
            }
        }
    }
}
