// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader.ui

import androidx.activity.compose.BackHandler
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import io.github.kasaco223.kdownloader.MainViewModel
import io.github.kasaco223.kdownloader.Screen
import io.github.kasaco223.kdownloader.ui.about.AboutScreen
import io.github.kasaco223.kdownloader.ui.about.LicenseScreen
import io.github.kasaco223.kdownloader.ui.home.HomeScreen

/** Raíz de MainActivity: muestra la pantalla actual. «Atrás» solo se intercepta fuera del inicio. */
@Composable
fun AppRoot(viewModel: MainViewModel) {
    val screen by viewModel.screen.collectAsStateWithLifecycle()
    val receivedLink by viewModel.receivedLink.collectAsStateWithLifecycle()

    BackHandler(enabled = screen != Screen.HOME) { viewModel.back() }

    when (screen) {
        Screen.HOME -> HomeScreen(
            receivedLink = receivedLink,
            onDismissLink = viewModel::dismissLink,
            onOpenAbout = { viewModel.open(Screen.ABOUT) },
        )
        Screen.ABOUT -> AboutScreen(
            onBack = { viewModel.back() },
            onOpenLicense = { viewModel.open(Screen.LICENSE) },
        )
        Screen.LICENSE -> LicenseScreen(onBack = { viewModel.back() })
    }
}
