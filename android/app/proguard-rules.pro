# JS-Schnittstelle window.WochenkorbApp: Methoden mit @JavascriptInterface duerfen weder entfernt noch umbenannt werden.
-keepclassmembers class io.github.legacylithiumx.wochenkorb.WochenkorbSchnittstelle {
    @android.webkit.JavascriptInterface <methods>;
}
