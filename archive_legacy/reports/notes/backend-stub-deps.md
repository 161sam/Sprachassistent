# Replace stubbed audio dependencies

## Context
The repository contained minimal placeholder modules (`torch.py`, `torchaudio.py`, `soundfile.py`, `piper/__init__.py`) used to satisfy imports when real libraries were unavailable.

## Design
- Remove the stub modules so the real packages from `requirements.txt` are used.
- In unit tests, guard imports with `pytest.importorskip` to skip gracefully if the heavy dependencies are missing.
- No changes to production code required beyond relying on genuine libraries.

