// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
package io.github.kasaco223.kdownloader.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class UrlsTest {
    // ------------------------------------------------------------------ mismos resultados que Windows
    @Test
    fun extractMatchesDesktop() = assertAll(DesktopUrlVectors.EXTRACT) { Urls.extract(it) }

    @Test
    fun coerceMatchesDesktop() = assertAll(DesktopUrlVectors.COERCE) { Urls.coerce(it) }

    @Test
    fun hasListParamMatchesDesktop() = assertAll(DesktopUrlVectors.HAS_LIST_PARAM) { Urls.hasListParam(it) }

    @Test
    fun isPlaylistPageMatchesDesktop() = assertAll(DesktopUrlVectors.IS_PLAYLIST_PAGE) { Urls.isPlaylistPage(it) }

    @Test
    fun guessVideoIdMatchesDesktop() = assertAll(DesktopUrlVectors.GUESS_VIDEO_ID) { Urls.guessVideoId(it) }

    @Test
    fun validateMatchesDesktop() = assertAll(DesktopUrlVectors.VALIDATE) { Urls.validate(it) }

    @Test
    fun isYoutubeMatchesDesktop() = assertAll(DesktopUrlVectors.IS_YOUTUBE) { Urls.isYoutube(it) }

    // ------------------------------------------------------------------ reglas propias de Android
    @Test
    fun extractRejectsLinksLongerThanTheEngineAccepts() {
        val base = "https://example.com/"
        val longest = base + "a".repeat(Urls.MAX_LENGTH - base.length)
        assertEquals(listOf(longest), Urls.extract(longest))
        // Windows lo muestra igual, pero media.validate_url (y el motor) lo rechazan: aquí no se ofrece.
        assertEquals(emptyList<String>(), Urls.extract(longest + "a"))
        assertNull(Urls.normalize(longest + "a"))
    }

    @Test
    fun validateCountsCodePointsLikePython() {
        val base = "https://example.com/"
        val emoji = String(Character.toChars(0x1F600)) // 2 char en Kotlin, 1 carácter en Python
        val atLimit = base + emoji.repeat(Urls.MAX_LENGTH - base.length)
        assertEquals(atLimit, Urls.validate(atLimit))
        assertNull(Urls.validate(atLimit + "a"))
    }

    @Test
    fun normalizeAcceptsOnlyHttpWithADottedHost() {
        assertEquals("https://www.youtube.com/watch?v=aqz-KE-bpKQ", Urls.normalize("https://youtube.com/watch?v=aqz-KE-bpKQ"))
        assertNull(Urls.normalize("http://localhost:8080/"))
        assertNull(Urls.normalize("file:///sdcard/video.mp4"))
        assertNull(Urls.normalize("content://media/external/video/1"))
        assertNull(Urls.normalize("javascript:alert(1)"))
        assertNull(Urls.normalize("kdownloader://download?url=x"))
        assertNull(Urls.normalize(""))
    }

    @Test
    fun extractHandlesTypicalShareTexts() {
        // YouTube (app): solo el enlace corto con ?si=.
        assertEquals(listOf("https://youtu.be/aqz-KE-bpKQ?si=4HrlPx7ZqcRk"), Urls.extract("https://youtu.be/aqz-KE-bpKQ?si=4HrlPx7ZqcRk"))
        // TikTok / Instagram: texto, salto de línea y enlace.
        assertEquals(
            listOf("https://vm.tiktok.com/ZMabc123/"),
            Urls.extract("Mira este video de @alguien en TikTok\nhttps://vm.tiktok.com/ZMabc123/ #fyp"),
        )
        // Título entre comillas tipográficas y enlace al final de la oración.
        assertEquals(
            listOf("https://www.youtube.com/watch?v=aqz-KE-bpKQ"),
            Urls.extract("“Big Buck Bunny”: https://m.youtube.com/watch?v=aqz-KE-bpKQ."),
        )
    }

    @Test
    fun extractKeepsTheOrderAndDropsRepeats() {
        val text = "https://b.com/2 https://a.com/1 https://B.com/2 https://a.com:443/1"
        assertEquals(listOf("https://b.com/2", "https://a.com/1"), Urls.extract(text))
    }

    @Test
    fun extractAndCoerceAcceptNullAndEmpty() {
        assertEquals(emptyList<String>(), Urls.extract(null))
        assertEquals(emptyList<String>(), Urls.extract(""))
        assertEquals(emptyList<String>(), Urls.coerce(null))
    }

    @Test
    fun hostFollowsPythonUrlparse() {
        assertEquals("www.youtube.com", Urls.host("https://WWW.YouTube.com:443/watch?v=x"))
        assertEquals("youtube.com", Urls.host("https://evil.example@youtube.com/"))
        assertEquals("::1", Urls.host("https://[::1]:8080/x"))
        assertNull(Urls.host("youtube.com/watch?v=x"))
        assertNull(Urls.host("https://[::1/x")) // Python: ValueError("Invalid IPv6 URL")
        assertNull(Urls.host(null))
    }

    @Test
    fun youtubeHelpersRejectGarbageWithoutThrowing() {
        val garbage = listOf("", " ", "%", "https://", "https://[", "http://\u0000/", "https://a.b/%", "https://a.b/?%zz=1")
        for (input in garbage) {
            Urls.extract(input)
            Urls.coerce(input)
            Urls.validate(input)
            assertFalse(input, Urls.isYoutube(input))
            Urls.hasListParam(input)
            Urls.isPlaylistPage(input)
            Urls.guessVideoId(input)
        }
        assertTrue(Urls.hasListParam("https://a.b/?%zz=1&list=x"))
    }

    private fun <T> assertAll(cases: List<Pair<String, T>>, actual: (String) -> T) {
        val failures = cases.mapNotNull { (input, expected) ->
            val got = actual(input)
            if (got == expected) null else "  ${quote(input)}\n    esperado: $expected\n    obtenido: $got"
        }
        assertTrue("${failures.size} de ${cases.size} casos no coinciden con Windows:\n" + failures.joinToString("\n"), failures.isEmpty())
    }

    private fun quote(s: String): String = buildString {
        append('"')
        for (c in s) if (c.code in 0x20..0x7E) append(c) else append("\\u%04X".format(c.code))
        append('"')
    }
}
