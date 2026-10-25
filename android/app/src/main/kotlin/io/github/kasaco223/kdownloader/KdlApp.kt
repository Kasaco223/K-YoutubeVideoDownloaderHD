// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader

import android.app.Application
import android.os.StrictMode

/**
 * La Application de K-Downloader. Más adelante arma aquí el grafo de dependencias (motor, cola de descargas,
 * ajustes) y los canales de notificación; en esta versión solo activa StrictMode en las compilaciones debug.
 */
class KdlApp : Application() {
    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) enableStrictMode()
    }

    /** Avisa en logcat (sin cerrar la app) de disco o red en el hilo principal y de recursos sin cerrar. */
    private fun enableStrictMode() {
        StrictMode.setThreadPolicy(
            StrictMode.ThreadPolicy.Builder().detectAll().penaltyLog().build(),
        )
        StrictMode.setVmPolicy(
            StrictMode.VmPolicy.Builder()
                .detectLeakedClosableObjects()
                .detectLeakedRegistrationObjects()
                .detectActivityLeaks()
                .detectFileUriExposure()
                .penaltyLog()
                .build(),
        )
    }
}
