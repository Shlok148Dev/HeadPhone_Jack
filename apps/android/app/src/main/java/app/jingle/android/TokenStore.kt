package app.jingle.android

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/** The Jingle scrobble token, encrypted at rest (Android Keystore). Never logged. */
object TokenStore {
    private const val KEY = "token"

    private fun prefs(ctx: Context): SharedPreferences {
        val master = MasterKey.Builder(ctx).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        return EncryptedSharedPreferences.create(
            ctx, "jingle", master,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun get(ctx: Context): String? = prefs(ctx).getString(KEY, null)
    fun set(ctx: Context, token: String) = prefs(ctx).edit().putString(KEY, token).apply()
    fun clear(ctx: Context) = prefs(ctx).edit().remove(KEY).apply()
}
