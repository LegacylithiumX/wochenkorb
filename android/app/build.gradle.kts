import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

// Release-Signatur: Zugangsdaten nur aus keystore.properties (nicht versioniert), nie im Skript.
val keystoreProps = Properties().apply {
    val datei = rootProject.file("keystore.properties")
    if (datei.exists()) datei.inputStream().use { load(it) }
}

android {
    namespace = "io.github.legacylithiumx.wochenkorb"
    compileSdk = 36

    defaultConfig {
        applicationId = "io.github.legacylithiumx.wochenkorb"
        minSdk = 24
        targetSdk = 36
        versionCode = 2
        versionName = "1.1"
    }

    signingConfigs {
        if (!keystoreProps.isEmpty) {
            create("release") {
                storeFile = rootProject.file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            signingConfigs.findByName("release")?.let { signingConfig = it }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlin {
        compilerOptions {
            jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
        }
    }
}

// Gebuendelte Kopie der Web-App: Copy-Task je Variante, AGP bindet das Ausgabeverzeichnis als assets/ ein
// (damit haengen Merge-, Lint- und Packaging-Aufgaben automatisch von der Kopie ab).
abstract class WebAppKopieren : Copy() {
    // Ausgabeverzeichnis fuer AGP (Assets-Wurzel); der Task schreibt darin nach www/
    @get:OutputDirectory
    abstract val ziel: DirectoryProperty
}

val webQuelle = rootProject.projectDir.parentFile

androidComponents {
    onVariants { variant ->
        val name = variant.name.replaceFirstChar { it.uppercase() }
        val kopie = tasks.register<WebAppKopieren>("kopiereWebApp$name") {
            description = "Kopiert index.html, Manifest, Service Worker, Icons und Preise nach assets/www/ ($name)"
            from(webQuelle) {
                include("index.html", "manifest.webmanifest", "sw.js", "icons/**", "daten/preise.json")
                into("www")
            }
            into(ziel)
        }
        variant.sources.assets?.addGeneratedSourceDirectory(kopie, WebAppKopieren::ziel)
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.ktx)
    implementation(libs.androidx.webkit)
}
