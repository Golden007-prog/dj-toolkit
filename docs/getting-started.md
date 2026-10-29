# Getting started

From nothing to a change you can see, in about ten minutes, on Windows or macOS. Just want to use the app? Download it instead: see the README.

## 1. Install

You need [Python 3.12](https://www.python.org/downloads/) (64-bit, from python.org: its installer includes the `py`
launcher) and [Git](https://git-scm.com/download/win). For the website you also need [Node.js 24](https://nodejs.org/).

```bat
git clone https://github.com/<you>/dj-toolkit.git
cd dj-toolkit
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\pre-commit install
```

On macOS the same steps are `python3.12 -m venv .venv`, `.venv/bin/pip install -r requirements-dev.txt` and
`.venv/bin/pre-commit install`; start the app with `./run.command` and check with `.venv/bin/python tools/check.py`.

`pre-commit install` makes git run ruff and a few file checks on every commit. It's optional; CI runs them anyway.

## 2. Run, check, look

```bat
run.bat
check.bat
.venv\Scripts\python tools\screenshots.py
```

The first starts the app. The second runs what CI runs (lint, format, about 160 tests, a minute). The third renders
every page in both looks into `screenshots\`, using a demo vocal and a throwaway settings folder.

## 3. The two-minute tour

| Open | To see |
|---|---|
| `djtoolkit/ui/main_window.py` | the sidebar, the three pages, the look switch |
| `djtoolkit/ui/acapella_tab.py` | the acapella workflow (the biggest file) |
| `djtoolkit/audio/align.py` | the four-beat grid: about 100 lines of NumPy, no Qt |
| `djtoolkit/spotify/engine.py` | scan, match, plan, apply: the whole sync in one function |
| `djtoolkit/ui/theme.py` | every colour, font, radius and spacing value |
| `tests/test_acapella_flow.py` | the workflow tested end to end, the way a user clicks |
| `docs/ux/VOICE.md` | how the app talks |

## 4. Make a first change

1. Pick a small one, like a tooltip: search the code for `Hear the count-in`.
2. Change the words, following [docs/ux/VOICE.md](ux/VOICE.md).
3. Run `check.bat --fix`.
4. Run `tools\screenshots.py` and look at both themes.
5. Commit on a branch (`git switch -c ui/better-tooltip`) and open a pull request.

## Common problems

| Problem | Fix |
|---|---|
| `py` isn't recognised | Install Python from python.org, not the Microsoft Store, or call `python` by its full path |
| `pip install` fails building something | You're on another Python version, or 32-bit Python. Use 64-bit Python 3.12 |
| "No audio output found" in the app | Windows sees no sound device. You can still place beats by eye; the tests don't need audio |
| Linking Spotify says port 8888 is busy | Close whatever uses it, or set `callback_port` in `%APPDATA%\DJToolkit\settings.json` and use the same port in your Spotify app's Redirect URI |
| `check.bat` fails on formatting | Run `check.bat --fix` |
| You're worried tests touch your settings | They can't: `tests/conftest.py` points `%APPDATA%` at a temporary folder |
