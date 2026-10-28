# Security

## Report a problem privately

Please don't open a public issue. Use GitHub's private reporting instead: open the repository's **Security** tab
and choose **Report a vulnerability**. You'll get a reply within a week. If the problem is real, it gets fixed,
you get credit if you want it, and an advisory is published.

## What is in scope

The app runs on your own computer, so the sensitive parts are few, and worth getting right:

- **Your Spotify login.** Linking uses Spotify's authorization code flow with PKCE, so no client secret is stored.
  The refresh token lives in `%APPDATA%\DJToolkit\token.json`. Anything that leaks it, or lets another program use
  it, is in scope.
- **The local sign-in listener.** While you link Spotify, the app listens on `127.0.0.1` (port 8888 by default) for
  up to three minutes and checks the `state` value Spotify sends back. Ways to abuse that listener are in scope.
- **Your music files.** The app reads your folders and writes new exports. It must never delete or overwrite your
  music. Anything that makes it do so is in scope.
- **Dependencies** with known vulnerabilities in the versions pinned in `requirements.txt` or `website/package-lock.json`.

Out of scope: attacks that need someone to already control your Windows account.

## Supported versions

The latest `main`. There are no releases yet.

## For contributors

Never commit keys, tokens, `.env` files or paths from your own machine; a test checks for them. A Spotify Client ID
isn't secret, but keep yours in the app, not in the repo.
