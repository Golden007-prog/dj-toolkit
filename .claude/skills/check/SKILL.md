---
name: check
description: Run DJ Toolkit's full check (ruff lint, ruff format, every test, the guardrails) and fix what fails. Use before saying any code change is done, before a commit or pull request, or when the user says check, verify, test or "make CI green".
---

# Check

1. From the repo root run `.venv\Scripts\python tools\check.py --fix`. It takes about a minute and runs exactly what
   CI runs.
2. If it fails, read the **first** failure and fix its cause in the code.
   - A guardrail test (`tests/test_guardrails.py`) names the rule it enforces and what to do instead. Follow it.
   - A theme test (`tests/test_theme.py`) means a colour pair is too low in contrast: adjust the palette in
     `djtoolkit/ui/theme.py` for every mode and accent it names.
3. Run the check again until it passes.
4. Never delete, skip or loosen a test, and never add to `KNOWN_COPY_DEBT`, to get a green run. If you believe a rule
   is wrong, stop and tell the user why; changing a rule is their call.
5. Report what failed, what you changed, and the final result in a sentence or two.
