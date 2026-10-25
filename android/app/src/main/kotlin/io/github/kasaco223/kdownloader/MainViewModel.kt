// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Pantallas de esta versión. La navegación completa (pestañas, Navigation 3) llega con el resto de la app. */
enum class Screen(val parent: Screen?) {
    HOME(null),
    ABOUT(HOME),
    LICENSE(ABOUT),
}

/**
 * Pantalla actual y enlace recibido por kdownloader://download. Todo vive en SavedStateHandle: sobrevive a la
 * rotación y a que Android cierre el proceso en segundo plano.
 */
class MainViewModel(private val savedState: SavedStateHandle) : ViewModel() {
    private val _screen = MutableStateFlow(
        savedState.get<String>(KEY_SCREEN)?.let { name -> Screen.entries.firstOrNull { it.name == name } } ?: Screen.HOME,
    )
    val screen: StateFlow<Screen> = _screen.asStateFlow()

    private val _receivedLink = MutableStateFlow(savedState.get<String>(KEY_LINK))
    val receivedLink: StateFlow<String?> = _receivedLink.asStateFlow()

    fun open(screen: Screen) {
        _screen.value = screen
        savedState[KEY_SCREEN] = screen.name
    }

    /** Vuelve a la pantalla anterior. False si ya está en el inicio (ahí «Atrás» lo maneja el sistema). */
    fun back(): Boolean {
        val parent = _screen.value.parent ?: return false
        open(parent)
        return true
    }

    fun onLinkReceived(url: String) {
        _receivedLink.value = url
        savedState[KEY_LINK] = url
        open(Screen.HOME)
    }

    fun dismissLink() {
        _receivedLink.value = null
        savedState[KEY_LINK] = null
    }

    companion object {
        private const val KEY_SCREEN = "screen"
        private const val KEY_LINK = "receivedLink"

        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer { MainViewModel(createSavedStateHandle()) }
        }
    }
}
