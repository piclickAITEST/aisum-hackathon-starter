/* Google sign-in via Firebase Auth.
 *
 * The config is NOT hardcoded here — it's fetched from /api/firebase-config, which
 * reads it from this server's env vars (see src/config.py). That's the one place a
 * project switch happens: personal account -> company project -> your team's
 * project is always just an env-var change, never an edit to this file.
 *
 * This is a module (the Firebase SDK is ESM-only on the CDN). app.js is a plain
 * script and cannot import it, so the parts app.js needs are hung on `window.__auth`.
 */
import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js';
import {
  getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged,
} from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js';

const $ = (id) => document.getElementById(id);

function fail(where, e) {
  const msg = `auth ${where}: ${e.code || e.message}`;
  for (const id of ['autherr', 'gate-err']) {
    const el = $(id);
    if (el) { el.hidden = false; el.textContent = msg; }
  }
  console.error('[auth]', where, e);
}

async function main() {
  let firebaseConfig;
  try {
    firebaseConfig = await (await fetch('/api/firebase-config')).json();
  } catch (e) {
    fail('config', e);
    return;
  }

  const auth = getAuth(initializeApp(firebaseConfig));

  // What app.js reads. `token()` returns a fresh ID token.
  window.__auth = {
    user: null,
    token: async () => (auth.currentUser ? auth.currentUser.getIdToken() : null),
  };

  onAuthStateChanged(auth, (user) => {
    window.__auth.user = user;
    const on = Boolean(user);
    document.body.classList.toggle('gated', !on);
    $('signin').hidden = on;
    $('signout').hidden = !on;
    $('whoami').hidden = !on;
    if (user) $('whoami').textContent = user.email || user.displayName || user.uid;
    window.dispatchEvent(new CustomEvent('authchange', { detail: { user } }));
  }, (e) => fail('state', e));

  async function signIn() {
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
    } catch (e) {
      // The two that actually happen: `auth/configuration-not-found` means Google
      // sign-in was never switched on for the project, and `auth/unauthorized-domain`
      // means the page's domain is not on Firebase's authorized-domains list.
      fail('signin', e);
    }
  }

  $('gate-signin').addEventListener('click', signIn);
  $('signin').addEventListener('click', signIn);
  $('signout').addEventListener('click', () => signOut(auth));
}

main();
