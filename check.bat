@echo off
rem Lint, format and the full test suite, exactly as CI runs them. Add --fix to let ruff fix what it can first.
cd /d "%~dp0"
".venv\Scripts\python.exe" tools\check.py %*
