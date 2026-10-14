/* Google sign-in via Firebase Auth.
 *
 * The config is NOT hardcoded here — it's fetched from /api/firebase-config, which
 * reads it from this server's env vars (see src/config.py). That's the one place a
 * project switch happens: personal account -> company project -> your team's
 * project is always just an env-var change, never an edit to this file.
 *
 * The Firebase SDK is ESM-only on the CDN. What app.js needs is hung on
 * `window.__auth`, and sign-in changes are announced as an `authchange` event.
 */
import { initializeApp } from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-app.js';
import {
  getAuth, GoogleAuthProvider, signInWithPopup, signOut, onAuthStateChanged,
} from 'https://www.gstatic.com/firebasejs/12.4.0/firebase-auth.js';

const $ = (id) => document.getElementById(id);

// The one sign-in error students actually hit is auth/unauthorized-domain, and what to do
// about it depends on which address the page was opened at, so say it where it shows up.
function hint(e) {
  if (!e || e.code !== 'auth/unauthorized-domain') return '';
  const host = location.hostname;
  if (host === 'localhost') return '';
  if (host.endsWith('.run.app')) {
    return ` | ${location.host} is not on the sign-in list yet. The organizers add Cloud Run ` +
           'addresses; if this stays after a while, send them this address.';
  }
  return ` | Sign-in is not allowed on ${location.host}. Open http://localhost:8000 in your ` +
         'browser. 127.0.0.1, and addresses that VS Code port forwarding or a tunnel gives ' +
         'you, do not work.';
}

function fail(where, e) {
  const msg = `auth ${where}: ${e.code || e.message}${hint(e)}`;
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

  window.__auth = {
    user: null,
    token: async () => (auth.currentUser ? auth.currentUser.getIdToken() : null),
  };

  onAuthStateChanged(auth, (user) => {
    window.__auth.user = user;
    const on = Boolean(user);
    document.body.classList.toggle('gated', !on);
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
      // means the page's domain is not on Firebase's authorized-domains list — most
      // often because the page was opened as 127.0.0.1:8000, which is not on it by
      // default. localhost:8000 is.
      fail('signin', e);
    }
  }

  $('gate-signin').addEventListener('click', signIn);
  $('signout').addEventListener('click', () => signOut(auth));
}

main();
