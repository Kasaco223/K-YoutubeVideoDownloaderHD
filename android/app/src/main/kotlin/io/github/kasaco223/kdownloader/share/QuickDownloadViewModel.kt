// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader.share

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Estado de la hoja que aparece al compartir. Sobrevive a la rotación (ViewModel) y a que Android cierre el
 * proceso (SavedStateHandle): el intent solo se lee en el primer onCreate y en onNewIntent, porque después de
 * una rotación getIntent() puede devolver el intent viejo.
 */
class QuickDownloadViewModel(private val savedState: SavedStateHandle) : ViewModel() {
    private val _link = MutableStateFlow(
        SharedLink(url = savedState.get<String>(KEY_URL), total = savedState.get<Int>(KEY_TOTAL) ?: 0),
    )
    val link: StateFlow<SharedLink> = _link.asStateFlow()

    fun reset(link: SharedLink) {
        _link.value = link
        savedState[KEY_URL] = link.url
        savedState[KEY_TOTAL] = link.total
    }

    companion object {
        private const val KEY_URL = "url"
        private const val KEY_TOTAL = "total"

        val Factory: ViewModelProvider.Factory = viewModelFactory {
            initializer { QuickDownloadViewModel(createSavedStateHandle()) }
        }
    }
}
