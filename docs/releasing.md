# Releasing

A release is a pull request that bumps the version. When it merges, the downloads build and publish themselves.

1. In a pull request, set `__version__` in `djtoolkit/__init__.py` (say `0.2.0`), and in `CHANGELOG.md` rename
   *Unreleased* to `[0.2.0] - <date>`, with a new empty *Unreleased* above it.
2. Once it's approved and merged, `.github/workflows/release.yml` finds a version without a release and, on Windows
   and on macOS:
   1. installs the app's dependencies and the build tools (`requirements-build.txt`);
   2. builds the app with PyInstaller (`packaging/dj-toolkit.spec`);
   3. runs the built app with `--self-test`, which fails the release if the assets, the tempo analysis, MP3 export
      (ffmpeg) or Qt don't work inside the bundle;
   4. packs `DJ-Toolkit-Windows.zip` and `DJ-Toolkit-macOS.dmg`.
3. It publishes them as release `v0.2.0`, with that version's CHANGELOG notes and the merged pull requests, then
   rebuilds the website so the download buttons point at the new files.

Nothing is published if a build or a self-test fails: fix it in another pull request, and the release happens when
that one merges. Published version tags can't be moved or deleted (ruleset *Release tags stay put*).

The file names never change, so `https://github.com/tomgreef/dj-toolkit/releases/latest/download/DJ-Toolkit-Windows.zip`
always points at the newest build. The website shows its download buttons only once a release has both files.

## Build it yourself

```bat
.venv\Scripts\pip install -r requirements-build.txt
.venv\Scripts\python -m PyInstaller --noconfirm packaging/dj-toolkit.spec
"dist\DJ Toolkit\DJ Toolkit.exe" --self-test
```

On macOS the app is `dist/DJ Toolkit.app`. To try the release workflow without publishing anything, run it from the
Actions tab (*Run workflow*): it builds and uploads the files as artifacts only. Pull requests that touch the
packaging or the dependencies run it too.

## Not done yet

- **Code signing.** The builds aren't signed, so Windows SmartScreen and macOS Gatekeeper warn on first open; the
  install steps say how to get past that. Signing needs a paid Windows certificate and an Apple Developer account.
- **Intel Macs.** The macOS build is for Apple silicon. An Intel build needs an Intel runner (or a universal build).
- **An installer for Windows.** The zip runs anywhere without admin rights; a setup program could add a Start menu
  entry and an uninstaller.
- **The app icon** is `packaging/icon.png`, drawn by `tools/make_icon.py` from the brand mark.
