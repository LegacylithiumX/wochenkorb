package io.github.legacylithiumx.wochenkorb

import android.annotation.SuppressLint
import android.content.ActivityNotFoundException
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.FrameLayout
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.SystemBarStyle
import androidx.activity.enableEdgeToEdge
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.updatePadding
import androidx.webkit.WebViewAssetLoader
import java.net.URISyntaxException

class MainActivity : ComponentActivity() {

    private lateinit var webView: WebView
    private lateinit var zurueck: OnBackPressedCallback
    private lateinit var assetLoader: WebViewAssetLoader

    /** true, sobald die gebuendelte Kopie statt der Hauptseite angezeigt wird. */
    private var kopieAktiv = false
    private var historieLeeren = false

    override fun onCreate(savedInstanceState: Bundle?) {
        val gruen = ContextCompat.getColor(this, R.color.gruen)
        // Statusleiste und Navigationsleiste in der Markenfarbe, helle Symbole.
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(gruen),
            navigationBarStyle = SystemBarStyle.dark(gruen),
        )
        super.onCreate(savedInstanceState)

        assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/assets/", WebViewAssetLoader.AssetsPathHandler(this))
            .build()

        webView = WebView(this).apply {
            layoutParams = FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
            konfigurieren()
            webViewClient = Client()
            addJavascriptInterface(WochenkorbSchnittstelle(this@MainActivity), SCHNITTSTELLE)
        }

        // Kein Ueberlappen mit Systemleisten: Insets als Padding, dahinter scheint die Markenfarbe.
        val wurzel = FrameLayout(this).apply {
            setBackgroundColor(gruen)
            addView(webView)
        }
        ViewCompat.setOnApplyWindowInsetsListener(wurzel) { ansicht, insets ->
            val rand = insets.getInsets(
                WindowInsetsCompat.Type.systemBars() or
                    WindowInsetsCompat.Type.displayCutout() or
                    WindowInsetsCompat.Type.ime(),
            )
            ansicht.updatePadding(rand.left, rand.top, rand.right, rand.bottom)
            WindowInsetsCompat.CONSUMED
        }
        setContentView(wurzel)

        // Zurueck: erst WebView-Verlauf, danach (Callback aus) beendet das System die Activity.
        zurueck = object : OnBackPressedCallback(false) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) webView.goBack()
            }
        }
        onBackPressedDispatcher.addCallback(this, zurueck)

        // Nach Prozesstod: letzte Seite samt Verlauf wiederherstellen, sonst Hauptseite laden.
        val wiederhergestellt = savedInstanceState?.let { webView.restoreState(it) } != null
        if (!wiederhergestellt) webView.loadUrl(START_URL)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun WebView.konfigurieren() {
        settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            cacheMode = WebSettings.LOAD_DEFAULT
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
            allowFileAccess = false
            allowContentAccess = false
            setSupportMultipleWindows(false)
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
    }

    override fun onPause() {
        webView.onPause()
        super.onPause()
    }

    override fun onDestroy() {
        (webView.parent as? ViewGroup)?.removeView(webView)
        webView.removeJavascriptInterface(SCHNITTSTELLE)
        webView.stopLoading()
        webView.webViewClient = WebViewClient()
        webView.destroy()
        super.onDestroy()
    }

    private fun ladeKopie() {
        if (kopieAktiv) return
        kopieAktiv = true
        historieLeeren = true
        webView.loadUrl(KOPIE_URL)
    }

    private inner class Client : WebViewClient() {

        override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
            if (darfInWebView(request.url)) return false
            extern(request.url)
            return true
        }

        override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? =
            assetLoader.shouldInterceptRequest(request.url)

        override fun onPageStarted(view: WebView, url: String?, favicon: Bitmap?) {
            // Wieder auf der Hauptseite (z.B. nach Neustart mit Netz): Kopie-Modus verlassen.
            if (url != null && url.startsWith(START_URL)) kopieAktiv = false
        }

        override fun onPageFinished(view: WebView, url: String?) {
            // Erst wenn die Kopie selbst fertig geladen ist, die fehlgeschlagene Hauptseite aus dem Verlauf werfen.
            if (historieLeeren && url != null && url.startsWith(KOPIE_URL)) {
                historieLeeren = false
                view.clearHistory()
                zurueck.isEnabled = false
            }
        }

        override fun doUpdateVisitedHistory(view: WebView, url: String?, isReload: Boolean) {
            zurueck.isEnabled = view.canGoBack()
        }

        override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
            if (request.isForMainFrame && !kopieAktiv) ladeKopie()
        }

        override fun onReceivedHttpError(view: WebView, request: WebResourceRequest, errorResponse: WebResourceResponse) {
            if (request.isForMainFrame && !kopieAktiv && errorResponse.statusCode >= 400) ladeKopie()
        }
    }

    /** Nur die eigene Seite und die gebuendelte Kopie bleiben in der WebView, alles andere geht nach aussen. */
    private fun darfInWebView(uri: Uri): Boolean {
        val schema = uri.scheme?.lowercase() ?: return false
        if (schema == "about") return uri.toString() == "about:blank"
        if (schema != "https") return false
        val host = uri.host?.lowercase() ?: return false
        if (host == KOPIE_HOST) return true
        val pfad = uri.path.orEmpty()
        return host == START_HOST && (pfad == "/wochenkorb" || pfad.startsWith("/wochenkorb/"))
    }

    private fun extern(uri: Uri) {
        when (uri.scheme?.lowercase()) {
            // Innere Schemas der WebView nie nach aussen geben.
            null, "file", "content", "javascript", "data", "blob", "about" -> return
            "intent" -> externIntentSchema(uri)
            else -> starte(Intent(Intent.ACTION_VIEW, uri).addCategory(Intent.CATEGORY_BROWSABLE))
        }
    }

    private fun externIntentSchema(uri: Uri) {
        val intent = try {
            Intent.parseUri(uri.toString(), Intent.URI_INTENT_SCHEME)
        } catch (_: URISyntaxException) {
            return
        }
        // Entschaerfen: kein festes Ziel, kein Selector, nur BROWSABLE-Ziele.
        intent.component = null
        intent.selector = null
        intent.addCategory(Intent.CATEGORY_BROWSABLE)
        if (!starte(intent, meldung = false)) {
            val ausweich = intent.getStringExtra("browser_fallback_url")?.let(Uri::parse)
            if (ausweich != null && ausweich.scheme.equals("https", ignoreCase = true)) {
                extern(ausweich)
            } else {
                Toast.makeText(this, R.string.kein_ziel, Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun starte(intent: Intent, meldung: Boolean = true): Boolean =
        try {
            startActivity(intent)
            true
        } catch (_: ActivityNotFoundException) {
            if (meldung) Toast.makeText(this, R.string.kein_ziel, Toast.LENGTH_SHORT).show()
            false
        }

    private companion object {
        const val SCHNITTSTELLE = "WochenkorbApp"
        const val START_HOST = "legacylithiumx.github.io"
        const val START_URL = "https://$START_HOST/wochenkorb/"
        const val KOPIE_HOST = WebViewAssetLoader.DEFAULT_DOMAIN
        const val KOPIE_URL = "https://$KOPIE_HOST/assets/www/index.html"
    }
}
