package app.jingle.android

import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.webkit.JavaScriptReplyProxy
import androidx.webkit.WebViewCompat
import androidx.webkit.WebViewFeature
import org.json.JSONObject

/**
 * Jingle itself (the web app) plus one bridge, `window.JingleAndroid`, offered only to Jingle's own
 * origin. The page hands over a scrobble token after the listener taps their music app
 * (D-CONNECT-01); the app then opens Android's notification-access toggle once. That's the setup.
 *
 * Messages (JSON strings):
 *   page → app: {type:"status"} | {type:"pair", token} | {type:"unpair"}
 *   app → page: {type:"status", paired, access} (also sent on every return to the app)
 */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private var page: JavaScriptReplyProxy? = null
    private val origin: String = Uri.parse(BuildConfig.JINGLE_URL).let { "${it.scheme}://${it.authority}" }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.webViewClient = object : WebViewClient() {
            // Jingle stays in the app; music apps, Spotify/Last.fm/Apple logins open where they belong.
            override fun shouldOverrideUrlLoading(view: WebView, req: WebResourceRequest): Boolean {
                val u = req.url
                if ("${u.scheme}://${u.authority}" == origin) return false
                startActivity(Intent(Intent.ACTION_VIEW, u))
                return true
            }
        }
        if (WebViewFeature.isFeatureSupported(WebViewFeature.WEB_MESSAGE_LISTENER)) {
            WebViewCompat.addWebMessageListener(web, "JingleAndroid", setOf(origin)) { _, message, source, isMainFrame, reply ->
                if (!isMainFrame || source.toString().trimEnd('/') != origin) return@addWebMessageListener
                page = reply
                val m = runCatching { JSONObject(message.data ?: "") }.getOrNull() ?: return@addWebMessageListener
                when (m.optString("type")) {
                    "pair" -> {
                        val token = m.optString("token")
                        if (token.length in 20..512) {
                            TokenStore.set(this, token)
                            if (!PlayListener.hasAccess(this)) askForAccess()
                        }
                    }
                    "unpair" -> TokenStore.clear(this)
                }
                sendStatus()
            }
        }
        setContentView(web)
        web.loadUrl(intent?.data?.takeIf { "${it.scheme}://${it.authority}" == origin }?.toString() ?: "$origin/home")
    }

    /** Android's own screen with one toggle for Jingle (the only permission the app needs). */
    private fun askForAccess() {
        startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
    }

    private fun sendStatus() {
        val s = JSONObject()
            .put("type", "status")
            .put("paired", TokenStore.get(this) != null)
            .put("access", PlayListener.hasAccess(this))
        page?.postMessage(s.toString())
    }

    override fun onResume() {
        super.onResume()
        sendStatus() // back from the toggle: the page flips to "Play a song to finish"
    }

    @Deprecated("Activity back handling")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }
}
