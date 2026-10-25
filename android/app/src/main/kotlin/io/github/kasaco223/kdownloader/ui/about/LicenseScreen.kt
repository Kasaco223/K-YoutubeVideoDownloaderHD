// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader.ui.about

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.produceState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import io.github.kasaco223.kdownloader.R
import io.github.kasaco223.kdownloader.ui.components.BackButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException

/** El texto completo de la GPL-3.0 que va dentro del APK, para leerlo sin conexión. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LicenseScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    val paragraphs by produceState<List<String>?>(initialValue = null, context) {
        value = withContext(Dispatchers.IO) { readLicense(context) }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.license_title)) },
                navigationIcon = { BackButton(onBack) },
            )
        },
    ) { innerPadding ->
        Box(
            Modifier
                .fillMaxSize()
                .padding(innerPadding),
            contentAlignment = Alignment.TopCenter,
        ) {
            val text = paragraphs
            when {
                text == null -> CircularProgressIndicator(Modifier.padding(32.dp))
                text.isEmpty() -> Text(
                    text = stringResource(R.string.license_load_failed),
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(16.dp),
                )
                else -> LazyColumn(
                    modifier = Modifier.widthIn(max = 720.dp),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Text(
                            text = stringResource(R.string.license_official_note),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    items(text) { paragraph ->
                        Text(text = paragraph, style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }
    }
}

/** Párrafos de la licencia; vacío si el archivo no está (no debería pasar: lo genera el build). */
private fun readLicense(context: Context): List<String> = try {
    context.assets.open(LicenseText.GPL_ASSET).bufferedReader(Charsets.UTF_8).use { LicenseText.paragraphs(it.readText()) }
} catch (ignored: IOException) {
    emptyList()
}
