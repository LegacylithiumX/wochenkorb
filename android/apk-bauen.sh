#!/usr/bin/env bash
# Baut die signierte Release-APK der Android-Huelle und legt sie als ../Wochenkorb.apk ab.
# Aufruf:  bash android/apk-bauen.sh
# Gebuendelt wird der aktuelle Stand von index.html, manifest.webmanifest, sw.js, icons/ und daten/preise.json.
# Wurde wochenkorb.html geaendert, vorher im Wurzelordner `bash bauen.sh` ausfuehren (erzeugt index.html).
cd "$(dirname "$0")" || exit 1

[ -f keystore.properties ] || { echo "keystore.properties fehlt - Release waere unsigniert."; exit 1; }
[ -n "$JAVA_HOME" ] || export JAVA_HOME="C:\\Program Files\\Android\\Android Studio\\jbr"
[ ../wochenkorb.html -nt ../index.html ] && echo "Hinweis: wochenkorb.html ist neuer als index.html - bauen.sh vergessen?"

./gradlew.bat assembleRelease --no-daemon --console=plain || exit 1

cp app/build/outputs/apk/release/app-release.apk ../Wochenkorb.apk || exit 1
ls -l ../Wochenkorb.apk
