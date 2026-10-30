# Releasing

A release is a pull request that bumps the version. When it merges, the downloads build and publish themselves.

1. In a pull request, set `__version__` in `djtoolkit/__init__.py` (say `0.2.0`), and in `CHANGELOG.md` rename
   *Unreleased* to `[0.2.0] - <date>`, with a new empty *Unreleased* above it.
2. Once it's approved and merged, `.github/workflows/release.yml` finds a version without a release and, on Windows
   and on macOS:
   1. installs the app's dependencies and the build tools (`requirements-build.txt`);
   2. lists the libraries the app is built from, in `DJ-Toolkit-Windows.cdx.json` or `DJ-Toolkit-macOS.cdx.json`
      (`tools/make_sbom.py`);
   3. builds the app with PyInstaller (`packaging/dj-toolkit.spec`);
   4. runs the built app with `--self-test`, which fails the release if the assets, the tempo analysis, MP3 export
      (ffmpeg) or Qt don't work inside the bundle;
   5. packs `DJ-Toolkit-Windows.zip` and `DJ-Toolkit-macOS.dmg`.
3. It has GitHub sign a record of where the two downloads and the two lists were built (an *attestation*), then
   publishes them as release `v0.2.0`, with `SHA256SUMS.txt`, that version's CHANGELOG notes and the merged pull
   requests, then rebuilds the website so the download buttons point at the new files.
   [Check a download](#check-a-download) says how anyone can use that record.
4. When that run finishes, `.github/workflows/announce-release.yml` posts the release in Discussions, in
   *Announcements*: the CHANGELOG notes and a link to the release page. It is a separate workflow, so a failure
   there never touches the release.

Nothing is published if a build, a self-test or the signing fails: fix it in another pull request, and the release
happens when that one merges. Published version tags can't be moved or deleted (ruleset *Release tags stay put*).

A release made with the default token doesn't start other workflows, so the announcement starts when the Release run
finishes (and when you publish a release by hand). A version that already has an announcement is skipped: delete the
discussion to post it again. To post an older release, or to read the post before it goes out, run *Announce release*
from the Actions tab: enter the tag, and leave *dry-run* ticked to print the post without making it.

The file names never change, so `https://github.com/tomgreef/dj-toolkit/releases/latest/download/DJ-Toolkit-Windows.zip`
always points at the newest build. The website shows its download buttons only once a release has both files.

## Check a download

You don't have to: the app is the same either way. These two checks are for anyone who wants to be sure before opening
a download, on a work laptop for instance. A release has `DJ-Toolkit-Windows.zip`, `DJ-Toolkit-macOS.dmg`,
`SHA256SUMS.txt` and two lists of libraries (below). Versions 0.1.0 and 0.1.1 came before this and have none of them.

**Was it built here?** When a release is built, GitHub signs a record of which repository and which commit (a saved
version of the code) each file was built from. Only this repository's workflows can sign one for it, so a copy built or
changed anywhere else has none. To read it, install the [GitHub CLI](https://cli.github.com), sign in once with
`gh auth login`, and run this in the folder that holds the download (use `DJ-Toolkit-macOS.dmg` for the Mac file):

```
gh attestation verify DJ-Toolkit-Windows.zip --repo tomgreef/dj-toolkit
```

It should say **Verification succeeded** and name `.github/workflows/release.yml` as the workflow that built the file.
If it says anything else, don't open the file. Download it again from the
[latest release](https://github.com/tomgreef/dj-toolkit/releases/latest), and if the check still fails, report it
privately ([SECURITY.md](../SECURITY.md)).

**Did it arrive whole?** `SHA256SUMS.txt` holds a fingerprint (SHA-256) of each file: a long number worked out from its
contents, which changes if even one byte does. On a Mac, run this in the folder with both files:

```
shasum -a 256 -c --ignore-missing SHA256SUMS.txt
```

It should print `DJ-Toolkit-macOS.dmg: OK`. On Windows, open PowerShell in the folder, run
`Get-FileHash DJ-Toolkit-Windows.zip`, and compare the `Hash` it prints with that file's line in `SHA256SUMS.txt`
(capital or small letters make no difference).

A matching fingerprint shows the file wasn't damaged on the way. It doesn't show who built it, because whoever could
swap a file could swap the list too. The first check covers that.

**What is inside?** `DJ-Toolkit-Windows.cdx.json` and `DJ-Toolkit-macOS.cdx.json` list the libraries in each app and
their versions (a software bill of materials, in the CycloneDX format), so a company or a security scanner can see what
the app is made of without opening it. They are signed like the downloads. The build writes each one from what it
installed for the app, plus Python, Qt and ffmpeg with the version each reports. They leave out the website's packages
and GitHub's own tools on purpose, because neither is in the download. They don't list libraries that a package carries
inside its own files (libsndfile inside `soundfile`, for instance), and they can include a Qt package whose parts the
build left out of the app. They come from the build machine, not from the finished app.

### After the next release (owner)

The signing step runs only when a release is published, so no pull request can try it: look at the first release that
has it.

1. Open the Release run for the push to `main`. In the *Publish v...* job, *Record where the downloads came from* is
   green and the run summary links the new attestation. The release page lists `SHA256SUMS.txt` and the two
   `.cdx.json` lists next to the two downloads.
2. Download the files into a new folder and check them the strict way, which also requires that this workflow made
   them, from `main`:

   ```
   gh release download v0.2.0 --repo tomgreef/dj-toolkit --dir check
   gh attestation verify check/DJ-Toolkit-Windows.zip --repo tomgreef/dj-toolkit \
     --signer-workflow tomgreef/dj-toolkit/.github/workflows/release.yml --source-ref refs/heads/main
   ```

   Do the same for `check/DJ-Toolkit-macOS.dmg` and the two `.cdx.json` lists. To see which commit a file was built
   from, add `--format json --jq '.[0].verificationResult.signature.certificate.sourceRepositoryDigest'` and compare it
   with the release's commit.
3. If the signing step fails, nothing is published and no tag is made. Run the failed jobs again from the Actions tab
   (*Re-run failed jobs*), or fix the cause in another pull request.

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
