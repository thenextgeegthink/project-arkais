# Project Arkais — Pre-Launch Demo Access Notice

> **Notice**: Arkais Studio v1 is currently operating in local-first demonstration mode. There is no remote backend, database server, or real user account management connected in this release.

## Demo Sign-In Gate
To evaluate the interface, the app is protected by a client-side gate. The demo credentials are pre-filled on load:

* **Email**: `researcher@arkais.lab`
* **Password**: `quantum-flux-2026`

Clicking **Sign In** sets an authentication flag in `localStorage` (`arkais_session = 'true'`), which maintains access across browser restarts until storage is cleared.

## Resetting Demo Session & Onboarding
To reset the demonstration state and review the Sign-In Gate or First-Run Welcome Card again:
1. Open your browser's Developer Tools (`F12` or `Cmd+Option+I`).
2. Navigate to **Application** > **Local Storage**.
3. Remove `arkais_session` to re-trigger the Sign-In Gate.
4. Remove `arkais_welcome_seen` to re-trigger the First-Run Welcome Card.
