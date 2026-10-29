# Dependencies

Every package this project installs on purpose, and why it is here: one row for each package named in
`requirements.txt`, `requirements-dev.txt`, `requirements-build.txt` and `website/package.json`. What those packages
install in turn isn't listed.

A test (`tests/test_repo_rules.py`) fails when a package has no row here, or a row names a package no dependency file
mentions any more. A new package then never arrives as one more quiet line: it arrives with its reason, ready for the
owner to read.

## Adding a package

A new package needs its own issue first ([AGENTS.md](../AGENTS.md)). Check it the way step 6 of
[Auditing an outside pull request](maintaining.md#auditing-an-outside-pull-request) says, then add one row in the same
pull request, with the name in backticks as the dependency file spells it. Fill in every cell:

- **Used for:** what in this project needs it, found by reading the code, not the package's own description.
- **Licence:** as published. This project is MIT, so a GPL or LGPL licence is named in the row and the owner decides.
- **Publisher and source repository:** who can publish a release, where the code lives and when the package first
  appeared. A package with one owner says so.
- **Checked:** the date, and who checked. A row an AI agent wrote says so, and the owner confirms it.

There is no version column on purpose: Dependabot's updates change versions, never this page.

## The packages

| Package | Used for | Licence | Publisher and source repository | Checked |
|---|---|---|---|---|
| `PySide6` | App: the windows and everything in them (Qt widgets and painting, audio playback through QtMultimedia, SVG icons through QtSvg). | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (PyPI metadata); its README says a commercial licence is also sold. | Qt for Python team, under the Qt organisation on PyPI; [code.qt.io/cgit/pyside/pyside-setup.git](https://code.qt.io/cgit/pyside/pyside-setup.git/); first release 2020. | 2026-10-29, by Claude Code (the owner confirms) |
| `librosa` | App: finds a track's tempo (BPM) and beat positions, opens audio files that `soundfile` can't read, and resamples audio for playback. | ISC | Brian McFee and the librosa team; sole PyPI owner `Brian.McFee`; [librosa/librosa](https://github.com/librosa/librosa); first release 2013. | 2026-10-29, by Claude Code (the owner confirms) |
| `soundfile` | App: opens audio files, and writes the exported WAV and FLAC files, the temporary WAV that ffmpeg turns into MP3, and the acapella preview. | BSD-3-Clause. Its wheels also carry the libsndfile library, which is LGPL (its README). | Bastian Bechtold; sole PyPI owner `bastibe`; [bastibe/python-soundfile](https://github.com/bastibe/python-soundfile); first release 2015. | 2026-10-29, by Claude Code (the owner confirms) |
| `numpy` | App: holds audio samples as arrays for tempo analysis, the waveform, playback and export. | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 (PyPI metadata; the wheels bundle other libraries). | NumPy developers, under the numpy organisation on PyPI; [numpy/numpy](https://github.com/numpy/numpy); first release 2006. | 2026-10-29, by Claude Code (the owner confirms) |
| `mutagen` | App: reads artist, title and album tags from music files for Spotify sync, and writes the BPM tag into exported files. | GPL-2.0-or-later, a copyleft licence (this project is MIT). | Christoph Reiter (the package's author) and the Quod Libet project; PyPI owners `lazka` and `phw`; [quodlibet/mutagen](https://github.com/quodlibet/mutagen); first release 2013. | 2026-10-29, by Claude Code (the owner confirms) |
| `requests` | App: the web calls to Spotify (linking, searches, playlists) and to GitHub (the ideas on the Requests page). | Apache-2.0 | The `psf` (Python Software Foundation) organisation on GitHub; PyPI owners `Lukasa`, `graffatcolmingov` and `nateprewitt`; [psf/requests](https://github.com/psf/requests); first release 2011. | 2026-10-29, by Claude Code (the owner confirms) |
| `imageio-ffmpeg` | App: supplies the ffmpeg program that turns an export into a 320 kbps MP3, the only thing ffmpeg does here. The release build copies that program into the app (`packaging/dj-toolkit.spec`). | BSD-2-Clause for the package. The ffmpeg program inside its wheels is built with `--enable-gpl` (the Windows one also with `--enable-version3`), so it is GPL (read from the Windows and macOS Apple silicon wheels, version 0.6.0). | imageio contributors; PyPI owners `Almar` and `FirefoxMetzger`; [imageio/imageio-ffmpeg](https://github.com/imageio/imageio-ffmpeg); first release 2019. The ffmpeg program comes from a second repository, [imageio/imageio-binaries](https://github.com/imageio/imageio-binaries), which has no licence file. | 2026-10-29, by Claude Code (the owner confirms) |
| `pytest` | Development: runs the tests in `tests/`, through `tools/check.py` and CI. | MIT | pytest-dev team; seven PyPI owners; [pytest-dev/pytest](https://github.com/pytest-dev/pytest); first release 2010. | 2026-10-29, by Claude Code (the owner confirms) |
| `ruff` | Development: the lint and format checks in `tools/check.py`, CI and the commit hooks. | MIT | Astral Software Inc.; PyPI owners `crmarsh`, `sarasklenka` and `zanie`; [astral-sh/ruff](https://github.com/astral-sh/ruff); first release 2022. | 2026-10-29, by Claude Code (the owner confirms) |
| `pre-commit` | Development: the optional git hooks that run ruff and file checks on each commit (`.pre-commit-config.yaml`). | MIT | Anthony Sottile; sole PyPI owner `asottile`; [pre-commit/pre-commit](https://github.com/pre-commit/pre-commit); first release 2014. | 2026-10-29, by Claude Code (the owner confirms) |
| `pyinstaller` | Building: packs the app and Python into the downloadable app (`packaging/dj-toolkit.spec`, `release.yml`). | GPL-2.0-or-later with a special exception that allows building and distributing non-free programs with it (PyPI metadata). | PyInstaller team; PyPI owner `Legorooj` and maintainer `bwoodsend`; [pyinstaller/pyinstaller](https://github.com/pyinstaller/pyinstaller); first release 2012. | 2026-10-29, by Claude Code (the owner confirms) |
| `pyinstaller-hooks-contrib` | Building: nothing here imports it. `pyinstaller` requires it and loads its recipes for libraries such as `librosa`, `soundfile` and `imageio-ffmpeg` by itself. | GPL-2.0-or-later for the hooks; Apache-2.0 for the runtime hooks that end up inside the built app (its LICENSE file). | PyInstaller team; PyPI owners `Legorooj`, `bjones`, `htgoebel` and `matysek`; [pyinstaller/pyinstaller-hooks-contrib](https://github.com/pyinstaller/pyinstaller-hooks-contrib); first release 2020. | 2026-10-29, by Claude Code (the owner confirms) |
| `pillow` | Building: lets PyInstaller turn `packaging/icon.png` into the Windows and macOS icon. The app doesn't import it, and the build leaves it out of the app. | MIT-CMU (a permissive licence; PyPI metadata). | Pillow team; PyPI owners `aclark`, `hugovk`, `radarhere` and `wiredfool`; [python-pillow/Pillow](https://github.com/python-pillow/Pillow); first release 2010 (a fork of the older PIL). | 2026-10-29, by Claude Code (the owner confirms) |
| `astro` | Website: builds the landing page in `website/` into a static site (`npm run build`, the Pages workflow). | MIT | The Astro project; npm maintainers `fredkschott` and `matthewp`; [withastro/astro](https://github.com/withastro/astro) (`packages/astro`); first release 2021. | 2026-10-29, by Claude Code (the owner confirms) |
