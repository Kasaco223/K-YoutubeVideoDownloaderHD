// SPDX-FileCopyrightText: 2026 Kasaco223 y colaboradores de K-Downloader
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Tareas que generan archivos que van dentro del APK. Viven en buildSrc (y no en app/build.gradle.kts)
// para que Gradle las cree con su ObjectFactory y sean compatibles con el configuration cache.
import org.gradle.api.DefaultTask
import org.gradle.api.GradleException
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.provider.Property
import org.gradle.api.tasks.CacheableTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.OutputDirectory
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.gradle.api.tasks.TaskAction
import java.security.MessageDigest

/**
 * assets/licenses/gpl-3.0.txt: el texto de android/LICENSE, que la pantalla «Acerca de» muestra sin
 * conexión (los «avisos legales apropiados» de la GPL-3.0, §0 y §5 d).
 *
 * Antes de copiarlo comprueba el SHA-256 del texto oficial de gnu.org: el APK nunca lleva una licencia
 * modificada por error (ci_repo_checks.sh revisa lo mismo en cada PR).
 */
@CacheableTask
abstract class KdLicenseAssetsTask : DefaultTask() {
    @get:InputFile
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val gplLicense: RegularFileProperty

    @get:Input
    abstract val gplSha256: Property<String>

    @get:OutputDirectory
    abstract val outputDir: DirectoryProperty

    @TaskAction
    fun copy() {
        val bytes = gplLicense.get().asFile.readBytes()
        val actual = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
        if (actual != gplSha256.get().lowercase()) {
            throw GradleException(
                "android/LICENSE no es el texto oficial de la GPL-3.0 (SHA-256 $actual, se esperaba " +
                    "${gplSha256.get()}). Restáuralo desde https://www.gnu.org/licenses/gpl-3.0.txt",
            )
        }
        val out = outputDir.get().asFile
        out.deleteRecursively()
        val target = out.resolve("licenses/gpl-3.0.txt")
        target.parentFile.mkdirs()
        target.writeBytes(bytes)
    }
}
