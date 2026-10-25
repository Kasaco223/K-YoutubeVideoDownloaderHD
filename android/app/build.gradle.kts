// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
import com.android.build.api.variant.FilterConfiguration
import java.io.StringReader
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.compose)
}

// ---- Versión: android/version.properties es la única fuente ------------------------------------------
val kdVersionName: String = Properties().apply {
    load(StringReader(providers.fileContents(rootProject.layout.projectDirectory.file("version.properties")).asText.get()))
}.getProperty("VERSION_NAME")?.trim() ?: error("Falta VERSION_NAME en android/version.properties")

val versionParts = Regex("""(0|[1-9]\d?)\.(0|[1-9]\d?)\.(0|[1-9]\d?)(?:-rc\.([1-9]\d?))?""")
    .matchEntire(kdVersionName)?.destructured
    ?: error("VERSION_NAME inválido: \"$kdVersionName\". Usa X.Y.Z o X.Y.Z-rc.N (X, Y y Z de 0 a 99).")
val (vMajor, vMinor, vPatch, vRc) = versionParts
val rcNumber: Int? = vRc.toIntOrNull()
require(rcNumber == null || rcNumber <= 98) { "VERSION_NAME: en X.Y.Z-rc.N, N va de 1 a 98 (99 es la estable)." }

// versionCode = base × 10 + dígito de ABI. Las rc quedan por debajo de su versión estable:
// 1.0.0-rc.1 → 10000011 / 10000013 / 10000014; 1.0.0 → 10000991 / 10000993 / 10000994.
val baseCode = vMajor.toInt() * 1_000_000 + vMinor.toInt() * 10_000 + vPatch.toInt() * 100 + (rcNumber ?: 99)
val abiDigit = mapOf("armeabi-v7a" to 1, "arm64-v8a" to 3, "x86_64" to 4) // 0 = APK sin dividir
val devAbi: String? = providers.gradleProperty("kdl.devAbi").orNull?.also {
    require(it in abiDigit) { "kdl.devAbi debe ser una de ${abiDigit.keys}" }
}

// Commit del código fuente (CI: KDL_SOURCE_COMMIT). "Acerca de" enlaza al árbol de ese commit.
val sourceCommit: String = providers.environmentVariable("KDL_SOURCE_COMMIT").orNull?.trim()
    ?.takeIf { Regex("[0-9A-Za-z._-]{1,64}").matches(it) } ?: "dev"

android {
    namespace = "io.github.kasaco223.kdownloader"
    // AGP 9.4 resuelve 37 como platforms;android-37.0. Compose 1.12 y core 1.19 lo exigen (minCompileSdk).
    compileSdk = 37

    defaultConfig {
        applicationId = "io.github.kasaco223.kdownloader" // no cambia nunca después del primer Release
        minSdk = 26
        targetSdk = 36 // explícito: en AGP 9, sin valor, tomaría compileSdk
        versionName = kdVersionName
        versionCode = baseCode * 10 // por variante; cada APK por ABI recibe el suyo abajo (onVariants)
        testInstrumentationRunner = "io.github.kasaco223.kdownloader.testing.KdlTestRunner"
        buildConfigField("String", "SOURCE_COMMIT", "\"$sourceCommit\"")
        buildConfigField("String", "REPO_URL", "\"https://github.com/Kasaco223/K-YoutubeVideoDownloaderHD\"")
        buildConfigField("String", "WEB_BASE", "\"https://kdownloader.vercel.app\"")
        if (devAbi != null) ndk { abiFilters += devAbi } // un solo APK (-Pkdl.devAbi=…); nunca junto con splits
    }

    flavorDimensions += "distribution"
    productFlavors {
        create("github") { dimension = "distribution" } // Releases de GitHub; "foss" (F-Droid) queda reservado
    }

    splits {
        abi {
            isEnable = devAbi == null
            reset()
            include("arm64-v8a", "armeabi-v7a", "x86_64")
            isUniversalApk = false
        }
    }

    signingConfigs {
        getByName("debug") { // llave de debug pública y versionada: los APK de prueba se instalan uno sobre otro
            storeFile = file("debug.keystore")
            storeType = "pkcs12"
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
        // Sin signingConfig de release: el APK de release sale sin firmar y se firma aparte con apksigner.
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
        create("qa") { // = release (R8) firmado con la llave de debug: el emulador de CI lo instala y lo abre
            initWith(getByName("release"))
            applicationIdSuffix = ".qa"
            versionNameSuffix = "-qa"
            signingConfig = signingConfigs.getByName("debug")
        }
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            signingConfig = signingConfigs.getByName("debug")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    packaging {
        jniLibs {
            useLegacyPackaging = true     // el motor (más adelante) ejecuta lib*.so desde nativeLibraryDir
            keepDebugSymbols += "**/*.so" // sin strip: los binarios quedan idénticos a los publicados
        }
        resources {
            // Archivos de licencia repetidos en varias dependencias: se conserva una copia.
            pickFirsts += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    androidResources {
        generateLocaleConfig = true // usa res/resources.properties (unqualifiedResLocale=en-US)
        localeFilters += listOf("en", "es")
    }

    dependenciesInfo { // bloque cifrado de Google Play: no aporta fuera de Play
        includeInApk = false
        includeInBundle = false
    }

    testOptions {
        animationsDisabled = true
    }

    lint {
        abortOnError = true
        checkReleaseBuilds = false // lint corre en CI sobre githubDebug
        checkDependencies = true   // revisa también :core (NewApi con minSdk 26: List.of, removeFirst…)
    }
}

// ---- Archivos generados que van al APK -------------------------------------------------------------------
val kdLicenseAssets = tasks.register<KdLicenseAssetsTask>("kdLicenseAssets") {
    gplLicense.set(rootProject.layout.projectDirectory.file("LICENSE"))
    gplSha256.set("3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986") // gnu.org/licenses/gpl-3.0.txt
    outputDir.set(layout.buildDirectory.dir("generated/kd/licenseAssets"))
}

androidComponents {
    onVariants { variant ->
        // versionCode por ABI (el dígito final también le dice a la app qué APK tiene instalado).
        variant.outputs.forEach { output ->
            val abi = output.filters.find { it.filterType == FilterConfiguration.FilterType.ABI }?.identifier ?: devAbi
            output.versionCode.set(baseCode * 10 + (abiDigit[abi] ?: 0))
        }
        variant.sources.assets?.addGeneratedSourceDirectory(kdLicenseAssets, KdLicenseAssetsTask::outputDir)
    }
}

dependencies {
    implementation(project(":core"))

    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.savedstate)
    implementation(libs.kotlinx.coroutines.android)

    testImplementation(libs.junit)

    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    androidTestImplementation(libs.androidx.test.core)
    androidTestImplementation(libs.androidx.test.runner)
    androidTestImplementation(libs.androidx.test.ext.junit)
}
