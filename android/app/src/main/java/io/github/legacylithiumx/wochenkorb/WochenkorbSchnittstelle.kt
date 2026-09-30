package io.github.legacylithiumx.wochenkorb

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.webkit.JavascriptInterface
import java.lang.ref.WeakReference

/**
 * window.WochenkorbApp fuer die Web-App.
 * Aufrufe kommen auf einem WebView-Hintergrundthread an, Intents werden auf dem Hauptthread gestartet.
 * Die Activity wird nur schwach gehalten; MainActivity entfernt die Schnittstelle in onDestroy.
 */
class WochenkorbSchnittstelle(activity: Activity) {

    private val activityRef = WeakReference(activity)

    @JavascriptInterface
    fun istApp(): Boolean = true

    @JavascriptInterface
    fun teilen(text: String?) {
        val inhalt = text?.takeIf { it.isNotBlank() } ?: return
        val activity = activityRef.get() ?: return
        activity.runOnUiThread { teilenImVordergrund(activity, inhalt) }
    }

    private fun teilenImVordergrund(activity: Activity, inhalt: String) {
        if (activity.isFinishing || activity.isDestroyed) return
        val senden = Intent(Intent.ACTION_SEND).apply {
            type = "text/plain"
            putExtra(Intent.EXTRA_TEXT, inhalt)
        }
        // Erst WhatsApp, dann WhatsApp Business; ist das Paket nicht installiert, wirft startActivity eine Ausnahme.
        for (paket in WHATSAPP_PAKETE) {
            try {
                activity.startActivity(Intent(senden).setPackage(paket))
                return
            } catch (_: ActivityNotFoundException) {
                // naechstes Paket probieren
            }
        }
        try {
            activity.startActivity(Intent.createChooser(senden, activity.getString(R.string.teilen_titel)))
        } catch (_: ActivityNotFoundException) {
            // keine Teilen-App vorhanden: nichts zu tun
        }
    }

    private companion object {
        val WHATSAPP_PAKETE = listOf("com.whatsapp", "com.whatsapp.w4b")
    }
}
