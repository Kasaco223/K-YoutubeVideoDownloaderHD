// Página de inicio.
import { initSite } from './site.js';
import { renderReleaseLabel } from './release.js';
import { initBookmarklet, initExampleButton, initOpenForm } from './open-app.js';

initSite();
initOpenForm(document.getElementById('open-form'));
initExampleButton(document.getElementById('open-example'), document.getElementById('open-url'));
initBookmarklet(document.getElementById('bookmarklet'), document.getElementById('bookmarklet-hint'));
renderReleaseLabel(document.getElementById('release-label'));
