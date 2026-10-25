// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader

import android.content.Intent
import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.appcompat.app.AppCompatActivity
import io.github.kasaco223.kdownloader.ui.AppRoot
import io.github.kasaco223.kdownloader.ui.theme.KdTheme

/**
 * La actividad del launcher (contrato A1). Pública: acepta el intent del launcher y el deep link
 * kdownloader://download?url=… (VIEW + BROWSABLE); no lee ningún otro extra.
 */
class MainActivity : AppCompatActivity() {
    private val viewModel: MainViewModel by viewModels { MainViewModel.Factory }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        // El intent solo se procesa en un arranque nuevo: ni al restaurar el estado ni al volver desde Recientes.
        val fromHistory = (intent.flags and Intent.FLAG_ACTIVITY_LAUNCHED_FROM_HISTORY) != 0
        if (savedInstanceState == null && !fromHistory) DeepLinks.url(intent)?.let(viewModel::onLinkReceived)
        setContent {
            KdTheme { AppRoot(viewModel) }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        DeepLinks.url(intent)?.let(viewModel::onLinkReceived)
    }
}
