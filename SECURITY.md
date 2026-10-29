# Security

## Report a problem privately

Please don't open a public issue. Use GitHub's private reporting instead: open the repository's **Security** tab
and choose **Report a vulnerability**. You'll get a reply within a week. If the problem is real, it gets fixed,
you get credit if you want it, and an advisory is published.

## What is in scope

The app runs on your own computer, so the sensitive parts are few, and worth getting right:

- **Your Spotify login.** Linking uses Spotify's authorization code flow with PKCE, so no client secret is stored.
  The refresh token lives in `token.json` in the app folder (`%APPDATA%\DJToolkit` on Windows,
  `~/Library/Application Support/DJToolkit` on macOS). Anything that leaks it, or lets another program use
  it, is in scope.
- **The local sign-in listener.** While you link Spotify, the app listens on `127.0.0.1` (port 8888 by default) for
  up to three minutes and checks the `state` value Spotify sends back. Ways to abuse that listener are in scope.
- **Your music files.** The app reads your folders and writes new exports. It must never delete or overwrite your
  music. Anything that makes it do so is in scope.
- **The Requests page** reads public issue data from GitHub and opens links in your browser; it never handles a
  GitHub login. Anything that makes it do more is in scope.
- **The downloads** are built in GitHub Actions from this repository's code, and new releases carry a signed record
  of where their files were built, plus checksums ([how to check](docs/releasing.md#check-a-download)). They
  aren't code-signed yet.
- **Dependencies** with known vulnerabilities in the versions pinned in the `requirements*.txt` files or
  `website/package-lock.json`.

Out of scope: attacks that need someone to already control your computer account.

## Supported versions

The latest release, and `main`.

## What's switched on

- **Private vulnerability reporting**, the button described above.
- **Dependabot alerts and security updates**, plus weekly version updates that wait a few days before proposing a
  new release, so a hijacked version has time to be caught ([docs/maintaining.md](docs/maintaining.md)).
- **Secret scanning with push protection:** a push that contains a known kind of key is refused.
- **Code scanning (CodeQL)** of the Python, the website and the GitHub Actions workflows, on every pull request
  and once a week.
- **Dependency review** on every pull request: a change that adds a dependency with a known vulnerability of
  moderate severity or worse can't merge.
- **Protected `main`:** changes arrive by pull request, a code owner approves, CI must pass, and published release
  tags can't be moved ([GOVERNANCE.md](GOVERNANCE.md)).
- **Least privilege in CI:** workflows get a read-only token unless a job asks for more, never keep the checkout's
  credentials, and use only GitHub's own actions (the one exception is OpenSSF Scorecard's, pinned to a commit).

## For contributors

Never commit keys, tokens, `.env` files or paths from your own machine; a test checks for them. A Spotify Client ID
isn't secret, but keep yours in the app, not in the repo.
