package app.jingle.android

import android.content.ComponentName
import android.content.Context
import android.media.MediaMetadata
import android.media.session.MediaController
import android.media.session.MediaSession
import android.media.session.MediaSessionManager
import android.media.session.PlaybackState
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.service.notification.NotificationListenerService

data class Track(val title: String, val artist: String, val album: String?, val durationMs: Long, val service: String)

/**
 * Sees what Spotify, YouTube Music, Amazon Music and Apple Music are playing through Android's
 * official media-session API, enabled by the one "notification access" toggle. Only these four
 * apps' sessions are read; notifications themselves are never read or stored.
 */
class PlayListener : NotificationListenerService() {
    companion object {
        val SERVICES = mapOf(
            "com.spotify.music" to "open.spotify.com",
            "com.google.android.apps.youtube.music" to "music.youtube.com",
            "com.amazon.mp3" to "music.amazon.com",
            "com.apple.android.music" to "music.apple.com",
        )
        private const val PLAYING_NOW_EVERY_MS = 45_000L // keeps Live fresh (Live = a signal under 90 s old)

        fun hasAccess(ctx: Context): Boolean {
            val me = ComponentName(ctx, PlayListener::class.java).flattenToString()
            val enabled = Settings.Secure.getString(ctx.contentResolver, "enabled_notification_listeners") ?: ""
            return enabled.split(':').any { it == me }
        }
    }

    private val main = Handler(Looper.getMainLooper())
    private val watchers = mutableMapOf<MediaSession.Token, Watcher>()
    private var msm: MediaSessionManager? = null
    private val onSessions = MediaSessionManager.OnActiveSessionsChangedListener { list -> watch(list ?: emptyList()) }
    private val heartbeat = object : Runnable {
        override fun run() {
            watchers.values.forEach { it.tick() }
            main.postDelayed(this, 15_000)
        }
    }

    override fun onListenerConnected() {
        val m = getSystemService(MediaSessionManager::class.java)
        msm = m
        val me = ComponentName(this, PlayListener::class.java)
        m.addOnActiveSessionsChangedListener(onSessions, me)
        watch(m.getActiveSessions(me))
        main.post(heartbeat)
    }

    override fun onListenerDisconnected() {
        main.removeCallbacks(heartbeat)
        msm?.removeOnActiveSessionsChangedListener(onSessions)
        watchers.values.forEach { it.stop() }
        watchers.clear()
    }

    private fun watch(controllers: List<MediaController>) {
        val ours = controllers.filter { it.packageName in SERVICES }
        val tokens = ours.map { it.sessionToken }.toSet()
        watchers.keys.filter { it !in tokens }.forEach { watchers.remove(it)?.stop() }
        for (c in ours) if (c.sessionToken !in watchers) watchers[c.sessionToken] = Watcher(c, SERVICES.getValue(c.packageName))
    }

    /** One player app: "playing now" while playing, and a listen once the song was really heard. */
    private inner class Watcher(private val c: MediaController, private val service: String) : MediaController.Callback() {
        private var track: Track? = null
        private var startedAt = 0L
        private var heardMs = 0L
        private var playingSince = 0L
        private var lastNowSent = 0L
        private var scrobbled = false

        init {
            c.registerCallback(this, main)
            onMetadataChanged(c.metadata)
            onPlaybackStateChanged(c.playbackState)
        }

        fun stop() {
            tick()
            c.unregisterCallback(this)
        }

        private fun playing() = c.playbackState?.state == PlaybackState.STATE_PLAYING

        override fun onMetadataChanged(m: MediaMetadata?) {
            val title = m?.getString(MediaMetadata.METADATA_KEY_TITLE)?.trim().orEmpty()
            val artist = (m?.getString(MediaMetadata.METADATA_KEY_ARTIST) ?: m?.getString(MediaMetadata.METADATA_KEY_ALBUM_ARTIST))?.trim().orEmpty()
            if (title.isEmpty() || artist.isEmpty()) return
            val t = Track(title, artist, m?.getString(MediaMetadata.METADATA_KEY_ALBUM), m?.getLong(MediaMetadata.METADATA_KEY_DURATION) ?: 0, service)
            if (t.title == track?.title && t.artist == track?.artist) return
            tick() // close out the previous song
            track = t
            startedAt = System.currentTimeMillis() / 1000
            heardMs = 0
            scrobbled = false
            playingSince = if (playing()) System.currentTimeMillis() else 0
            lastNowSent = 0
            tick()
        }

        override fun onPlaybackStateChanged(s: PlaybackState?) {
            val now = System.currentTimeMillis()
            if (s?.state == PlaybackState.STATE_PLAYING) {
                if (playingSince == 0L) playingSince = now
            } else if (playingSince != 0L) {
                heardMs += now - playingSince
                playingSince = 0
            }
            tick()
        }

        /** Refreshes "playing now" and submits the listen at the ListenBrainz threshold (half, max 4 min). */
        fun tick() {
            val t = track ?: return
            val now = System.currentTimeMillis()
            if (playing() && now - lastNowSent >= PLAYING_NOW_EVERY_MS) {
                Submitter.send(this@PlayListener, "playing_now", t)
                lastNowSent = now
            }
            val heard = heardMs + if (playingSince != 0L) now - playingSince else 0
            val need = if (t.durationMs > 0) minOf(t.durationMs / 2, 240_000) else 240_000
            if (!scrobbled && heard >= need) {
                Submitter.send(this@PlayListener, "single", t, startedAt)
                scrobbled = true
            }
        }
    }
}
